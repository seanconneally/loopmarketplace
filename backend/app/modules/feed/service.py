import hashlib
import json
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import DomainError, require
from app.core.outbox import emit
from app.core.paging import cursor_time, decode_cursor, encode_cursor
from app.core.redis import client, command
from app.modules.feed.models import Candidate
from app.modules.feed.ranking import (
    FeedRanker,
    HeuristicRanker,
    InterestProfile,
    build_profile,
    recommend,
)
from app.modules.feed.repository import FeedRepository
from app.modules.feed.schemas import FeedFilters, FeedOptions, FeedPage
from app.modules.listings.schemas import ListingView


class FeedService:
    def __init__(self, session: AsyncSession, ranker: FeedRanker | None = None) -> None:
        self.session, self.repo = session, FeedRepository(session)
        self.ranker = ranker or HeuristicRanker()

    async def dismiss(self, user: UUID, listing: UUID) -> None:
        from app.modules.analytics.service import AnalyticsService
        from app.modules.listings.service import ListingService

        await ListingService(self.session).detail(listing, user)
        await self.repo.dismiss(user, listing)
        await AnalyticsService(self.session).action(user, listing, "not_interested")

    async def undo_dismiss(self, user: UUID, listing: UUID) -> None:
        from app.modules.analytics.service import AnalyticsService

        await self.repo.undo_dismiss(user, listing)
        await AnalyticsService(self.session).undo_dismissal(user, listing)

    async def reset_preferences(self, user: UUID) -> None:
        """Ignore older signals without restoring explicitly hidden adverts."""
        await self.repo.reset(user)
        await emit(self.session, "analytics.withdrawn", {"user_id": str(user)})

    async def accepts_signal_time(self, user: UUID, created_at: datetime) -> bool:
        cutoff = await self.repo.cutoff(user)
        return cutoff is None or created_at > cutoff

    async def interest_profile(self, user: UUID, cutoff: datetime | None) -> InterestProfile:
        from app.modules.analytics.service import AnalyticsService

        since = max(cutoff or utcnow() - timedelta(days=30), utcnow() - timedelta(days=30))
        events = await AnalyticsService(self.session).recent(user, since)
        facts = (
            {
                row.listing_id: row
                for row in await self.repo.by_ids(list({event.listing_id for event in events}))
                if row.seller_id != user
            }
            if events
            else {}
        )
        return build_profile(events, facts, utcnow())

    async def options(self) -> FeedOptions:
        """Return available makes from published inventory instead of a hard-coded UI list."""
        return FeedOptions(makes=await self.repo.makes())

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
                "category": listing.category,
                "make": listing.car.make if listing.car else None,
                "year": listing.car.year if listing.car else None,
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
        """Adapt unseen pages to fresh signals; committed pages remain stable on retry."""
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
        if filters.sort != "recommended":
            return await self._ordered(filters, user, fingerprint, identity, state)
        from app.modules.users.service import UserService

        consented = bool(user and (await UserService(self.session).active(user)).analytics_consent)
        cutoff = await self.repo.cutoff(user) if user and consented else None
        preference_version = f"{consented}:{cutoff.isoformat() if cutoff else ''}"
        if state:
            require(
                state.get("preferences") == preference_version,
                410,
                "cursor_expired",
                "Your feed preferences changed. Refresh to continue.",
            )
        try:
            initial: list[Candidate] | None = None
            if state:
                require(
                    state.get("version") == 2,
                    410,
                    "cursor_expired",
                    "Refresh your feed to continue.",
                )
                snapshot_id, start = str(state["snapshot"]), int(state["position"])
            else:
                cell = f"{round(filters.latitude, 1)}:{round(filters.longitude, 1)}"
                revision = await client.get(f"feed:revision:{filters.region_id}") or "0"
                cache_key = f"feed:candidates:{filters.region_id}:{cell}:{revision}:{fingerprint}"
                cached = await client.get(cache_key)
                if cached:
                    initial = await self.repo.by_ids([UUID(value) for value in json.loads(cached)])
                else:
                    initial = await self.repo.candidates(filters)
                    await client.set(
                        cache_key, json.dumps([str(row.listing_id) for row in initial]), ex=30
                    )
                snapshot_id, start = secrets.token_urlsafe(18), 0
                await client.set(
                    f"feed:snapshot:{snapshot_id}",
                    json.dumps(
                        {
                            "ids": [str(row.listing_id) for row in initial],
                            "pages": {},
                            "frontier": 0,
                        }
                    ),
                    ex=1800,
                )
            key = f"feed:snapshot:{snapshot_id}"
            page_size = 4 if consented else 10
            # Publish a page once with compare-and-swap. Concurrent requests for the
            # same cursor converge on identical IDs, while unseen pages learn afresh.
            for _ in range(4):
                raw = await client.get(key)
                require(raw, 410, "cursor_expired", "Refresh the feed to continue.")
                snapshot = json.loads(raw or "{}")
                page = snapshot["pages"].get(str(start))
                if page is not None:
                    items = await self._visible(
                        [UUID(value) for value in page["ids"]], user, filters
                    )
                    position = int(page["next"])
                    break
                require(
                    start == snapshot["frontier"],
                    410,
                    "cursor_expired",
                    "Refresh the feed to continue.",
                )
                ids = snapshot["ids"]
                candidates = (
                    initial
                    if initial is not None
                    else await self.repo.by_ids([UUID(value) for value in ids[start:]])
                )
                candidate_ids = [str(item.listing_id) for item in candidates]
                membership = (
                    await command("SMISMEMBER", f"feed:seen:{identity}", *candidate_ids)
                    if consented and candidate_ids
                    else []
                )
                seen = {
                    listing
                    for listing, value in zip(candidate_ids, membership, strict=False)
                    if value
                }
                profile = (
                    await self.interest_profile(user, cutoff)
                    if user and consented
                    else InterestProfile()
                )
                ranked = recommend(candidates, utcnow(), seen, profile, self.ranker)
                ids = ids[:start] + [str(row.listing_id) for row in ranked]
                items, position = [], start
                while position < len(ids) and len(items) < page_size:
                    batch = ids[position : position + (page_size - len(items))]
                    position += len(batch)
                    items.extend(
                        await self._visible([UUID(value) for value in batch], user, filters)
                    )
                snapshot["ids"], snapshot["frontier"] = ids, position
                snapshot["pages"][str(start)] = {
                    "ids": [str(item.id) for item in items],
                    "next": position,
                }
                won = await command(
                    "EVAL",
                    "if redis.call('GET',KEYS[1])==ARGV[1] then redis.call('SET',KEYS[1],ARGV[2],'EX',1800); return 1 end; return 0",
                    1,
                    key,
                    raw or "",
                    json.dumps(snapshot),
                )
                if won:
                    break
            else:
                raise DomainError(409, "feed_busy", "Please retry this feed page.")
            next_cursor = (
                encode_cursor(
                    {
                        "version": 2,
                        "filters": fingerprint,
                        "user": identity,
                        "snapshot": snapshot_id,
                        "position": position,
                        "preferences": preference_version,
                    }
                )
                if position < len(snapshot["ids"])
                else None
            )
            return FeedPage(items=items, next_cursor=next_cursor, ranking="interest-v2")
        except RedisError:
            if state:
                raise DomainError(
                    410, "cursor_expired", "Feed ordering changed. Refresh to continue."
                ) from None
            return await self._recency(filters, user, fingerprint, identity, None)

    async def _visible(
        self, ids: list[UUID], user: UUID | None, filters: FeedFilters
    ) -> list[ListingView]:
        from app.modules.listings.service import ListingService
        from app.modules.moderation.service import ModerationService
        from app.modules.users.service import UserService

        visible = await ListingService(self.session).visible_ids(ids)
        rows = {
            row.listing_id: row for row in await self.repo.candidates(filters, len(ids), ids=ids)
        }
        peers = {row.seller_id for row in rows.values()}
        active = await UserService(self.session).active_names(peers)
        blocked = (
            await ModerationService(self.session).blocked_peers(user, peers) if user else set()
        )
        saved = await ListingService(self.session).saved_subset(user, ids) if user else set()
        dismissed = await self.repo.dismissed(user, ids) if user else set()
        results = []
        for listing_id in ids:
            if listing_id not in visible or listing_id not in rows or listing_id in dismissed:
                continue
            row = rows[listing_id]
            if row.seller_id in blocked or row.seller_id not in active:
                continue
            item = ListingView.model_validate(row.public_data)
            item.saved = listing_id in saved
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
        return await self._ordered(filters, user, fingerprint, identity, state, fallback=True)

    async def _ordered(
        self,
        filters: FeedFilters,
        user: UUID | None,
        fingerprint: str,
        identity: str,
        state: dict[str, object] | None,
        fallback: bool = False,
    ) -> FeedPage:
        """Use stable SQL keysets for explicit sorting, filling around hidden rows in bounded batches."""
        after = (cursor_time(str(state["time"])), UUID(str(state["id"]))) if state else None
        after_price = int(str(state["price"])) if state and "price" in state else None
        items: list[ListingView] = []
        last: Candidate | None = None
        more = False
        for _ in range(10):
            remaining = 10 - len(items)
            candidates = await self.repo.candidates(filters, remaining + 1, after, after_price)
            batch, more = candidates[:remaining], len(candidates) > remaining
            if not batch:
                break
            last = batch[-1]
            items.extend(await self._visible([row.listing_id for row in batch], user, filters))
            after, after_price = (last.published_at, last.listing_id), last.price_cents
            if len(items) == 10 or not more:
                break
        cursor = (
            encode_cursor(
                {
                    "mode": "recency" if fallback else "ordered",
                    "filters": fingerprint,
                    "user": identity,
                    "time": last.published_at.isoformat(),
                    "id": str(last.listing_id),
                    "price": last.price_cents,
                }
            )
            if last and more
            else None
        )
        return FeedPage(
            items=items,
            next_cursor=cursor,
            ranking="recency-fallback" if fallback else filters.sort,
        )
