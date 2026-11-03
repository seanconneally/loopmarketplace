import hashlib
import json
import secrets
from uuid import UUID

from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import DomainError, require
from app.core.outbox import emit
from app.core.paging import cursor_time, decode_cursor, encode_cursor
from app.core.redis import client, command
from app.modules.feed.models import Candidate
from app.modules.feed.ranking import FeedRanker, HeuristicRanker
from app.modules.feed.repository import FeedRepository
from app.modules.feed.schemas import FeedFilters, FeedPage
from app.modules.listings.schemas import ListingView


class FeedService:
    def __init__(self, session: AsyncSession, ranker: FeedRanker | None = None) -> None:
        self.session, self.repo = session, FeedRepository(session)
        self.ranker = ranker or HeuristicRanker()

    async def project(self, listing: ListingView, latitude: float, longitude: float) -> None:
        """Update our public projection through a module interface in the caller's transaction."""
        assert listing.published_at is not None
        await self.repo.upsert(
            {
                "listing_id": listing.id,
                "seller_id": listing.seller.id,
                "region_id": listing.region_id,
                "location": f"SRID=4326;POINT({longitude} {latitude})",
                "price_cents": listing.price_cents,
                "make": listing.car.make,
                "year": listing.car.year,
                "published_at": listing.published_at,
                "public_data": listing.model_dump(mode="json"),
            }
        )
        await emit(self.session, "feed.invalidate", {"region_id": listing.region_id})

    async def remove(self, listing: UUID) -> None:
        """Remove a candidate immediately; durable invalidation follows the commit."""
        await self.repo.remove(listing)
        await emit(self.session, "feed.invalidate", {"region_id": "ie-dublin"})

    async def page(self, filters: FeedFilters, user: UUID | None, cursor: str | None) -> FeedPage:
        """Freeze ranked candidates per browsing session; use keyset recency if Redis fails."""
        fingerprint = hashlib.sha256(filters.model_dump_json().encode()).hexdigest()[:20]
        identity = str(user) if user else "anonymous"
        state = decode_cursor(cursor) if cursor else None
        if state:
            require(
                state.get("filters") == fingerprint and state.get("user") == identity,
                400,
                "cursor_mismatch",
                "Restart the feed after changing filters or account.",
            )
        if state and state.get("mode") == "recency":
            return await self._recency(filters, user, fingerprint, identity, state)
        try:
            if state:
                snapshot = await client.get(f"feed:snapshot:{state['snapshot']}")
                require(snapshot, 410, "cursor_expired", "Refresh the feed to continue.")
                ids = json.loads(snapshot or "[]")
                position, snapshot_id = int(state["position"]), state["snapshot"]
            else:
                # Exact centre/filter fingerprint prevents a geographic cell cache admitting
                # out-of-radius items. Cell prefix permits later shared coarse candidates.
                cell = f"{round(filters.latitude, 1)}:{round(filters.longitude, 1)}"
                revision = await client.get(f"feed:revision:{filters.region_id}") or "0"
                cache_key = f"feed:candidates:{filters.region_id}:{cell}:{revision}:{fingerprint}"
                cached = await client.get(cache_key)
                if cached:
                    candidates = await self.repo.by_ids(
                        [UUID(value) for value in json.loads(cached)]
                    )
                else:
                    candidates = await self.repo.candidates(filters)
                    await client.set(
                        cache_key, json.dumps([str(row.listing_id) for row in candidates]), ex=30
                    )
                from app.modules.users.service import UserService

                consented = bool(
                    user and (await UserService(self.session).active(user)).analytics_consent
                )
                seen = (
                    set(await command("SMEMBERS", f"feed:seen:{identity}")) if consented else set()
                )
                now = utcnow()
                try:
                    candidates.sort(
                        key=lambda item: (
                            self.ranker.score(item, now, str(item.listing_id) in seen),
                            str(item.listing_id),
                        ),
                        reverse=True,
                    )
                except Exception:
                    return await self._recency(filters, user, fingerprint, identity, None)
                ids = [str(row.listing_id) for row in candidates]
                snapshot_id, position = secrets.token_urlsafe(18), 0
                await client.set(f"feed:snapshot:{snapshot_id}", json.dumps(ids), ex=300)
            items: list[ListingView] = []
            # Consume hidden IDs too, so removed/blocked items cannot trap a cursor.
            while position < len(ids) and len(items) < 10:
                batch = ids[position : position + (10 - len(items))]
                position += len(batch)
                items.extend(await self._visible([UUID(value) for value in batch], user))
            next_cursor = (
                encode_cursor(
                    {
                        "filters": fingerprint,
                        "user": identity,
                        "snapshot": snapshot_id,
                        "position": position,
                    }
                )
                if position < len(ids)
                else None
            )
            return FeedPage(items=items, next_cursor=next_cursor)
        except RedisError:
            if state:
                raise DomainError(
                    410, "cursor_expired", "Feed ordering changed. Refresh to continue."
                ) from None
            return await self._recency(filters, user, fingerprint, identity, None)

    async def _visible(self, ids: list[UUID], user: UUID | None) -> list[ListingView]:
        from app.modules.listings.service import ListingService
        from app.modules.moderation.service import ModerationService
        from app.modules.users.service import UserService

        visible = await ListingService(self.session).visible_ids(ids)
        rows = {row.listing_id: row for row in await self.repo.by_ids(ids)}
        results = []
        for listing_id in ids:
            if listing_id not in visible or listing_id not in rows:
                continue
            row = rows[listing_id]
            if user and await ModerationService(self.session).blocked(user, row.seller_id):
                continue
            try:
                await UserService(self.session).active(row.seller_id)
            except DomainError:
                continue
            item = ListingView.model_validate(row.public_data)
            if user:
                item.saved = await ListingService(self.session).is_saved(user, listing_id)
            results.append(item)
        return results

    async def _recency(
        self,
        filters: FeedFilters,
        user: UUID | None,
        fingerprint: str,
        identity: str,
        state: dict[str, object] | None,
    ) -> FeedPage:
        after = (cursor_time(str(state["time"])), UUID(str(state["id"]))) if state else None
        candidates = await self.repo.candidates(filters, 11, after)
        items = await self._visible([row.listing_id for row in candidates[:10]], user)
        last: Candidate | None = candidates[9] if len(candidates) > 10 else None
        cursor = (
            encode_cursor(
                {
                    "mode": "recency",
                    "filters": fingerprint,
                    "user": identity,
                    "time": last.published_at.isoformat(),
                    "id": str(last.listing_id),
                }
            )
            if last
            else None
        )
        return FeedPage(items=items, next_cursor=cursor, ranking="recency-fallback")
