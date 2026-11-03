import hashlib
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import require
from app.core.outbox import emit
from app.core.paging import cursor_time, decode_cursor, encode_cursor
from app.modules.listings.models import CarDetails, Listing, Save
from app.modules.listings.repository import ListingRepository
from app.modules.listings.schemas import (
    CarInput,
    ListingCreate,
    ListingPage,
    ListingUpdate,
    ListingView,
    SellerListingPage,
    SellerListingView,
)
from app.modules.users.service import UserService


class ListingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, ListingRepository(session)

    async def create(self, user: UUID, data: ListingCreate, key: str) -> Listing:
        """Create a draft once for a seller/key pair, rejecting conflicting replays."""
        owner = await UserService(self.session).active(user)
        require(
            owner.verified_at and owner.adult_declared,
            403,
            "seller_ineligible",
            "Verify your phone and confirm you are 18+.",
        )
        request_hash = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
        values = data.model_dump(exclude={"car"})
        result = await self.session.execute(
            insert(Listing)
            .values(
                **values,
                seller_id=user,
                idempotency_key=key,
                request_hash=request_hash,
            )
            .on_conflict_do_nothing(index_elements=["seller_id", "idempotency_key"])
            .returning(Listing.id)
        )
        new_id = result.scalar_one_or_none()
        listing = await self.repo.get(new_id) if new_id else await self.repo.by_key(user, key)
        assert listing is not None
        require(
            listing.request_hash == request_hash,
            409,
            "idempotency_conflict",
            "This key was used for a different listing.",
        )
        if new_id:
            self.session.add(CarDetails(listing_id=listing.id, **data.car.model_dump()))
            await emit(self.session, "listing.created", {"listing_id": str(listing.id)})
        await self.session.flush()
        return listing

    async def owned(self, listing_id: UUID, user: UUID, lock: bool = False) -> Listing:
        """Authorize ownership before editing a listing or uploading media."""
        listing = await self.repo.get(listing_id, lock=lock)
        require(listing, 404, "listing_missing", "Listing not found.")
        assert listing is not None
        require(listing.seller_id == user, 403, "not_owner", "Only the seller can do this.")
        return listing

    async def detail(self, listing_id: UUID, viewer: UUID | None = None) -> ListingView:
        """Build a public listing view through owning module interfaces."""
        from app.modules.media.service import MediaService
        from app.modules.moderation.service import ModerationService

        listing = await self.repo.get(listing_id)
        require(listing, 404, "listing_missing", "Listing not found.")
        assert listing is not None
        require(
            listing.status in {"live", "sold"} or viewer == listing.seller_id,
            404,
            "listing_missing",
            "Listing not found.",
        )
        if viewer:
            require(
                not await ModerationService(self.session).blocked(viewer, listing.seller_id),
                404,
                "listing_missing",
                "Listing not found.",
            )
        car = await self.repo.car(listing.id)
        assert car is not None
        media = await MediaService(self.session).playable(listing.id)
        return ListingView(
            id=listing.id,
            title=listing.title,
            description=listing.description,
            price_cents=listing.price_cents,
            currency=listing.currency,
            status=listing.status,
            area=listing.area,
            category=listing.category,
            region_id=listing.region_id,
            car=CarInput.model_validate(car),
            seller=await UserService(self.session).seller(listing.seller_id),
            playback_url=media.playback_url if media else None,
            poster_url=media.poster_url if media else None,
            duration=media.duration if media else None,
            published_at=listing.published_at,
            saved=await self.repo.saved(viewer, listing.id) if viewer else False,
            has_audio=media.has_audio if media else False,
        )

    async def media_state(self, listing_id: UUID, status: str) -> None:
        """Apply a processing result and update the feed via its public interface."""
        from app.modules.feed.service import FeedService

        listing = await self.repo.get(listing_id, lock=True)
        if (
            listing is None
            or listing.status == "removed"
            or (listing.status == "sold" and status != "removed")
        ):
            return
        if status == "live":
            owner = await UserService(self.session).active(listing.seller_id)
            require(
                owner.adult_declared and listing.rights_confirmed,
                403,
                "seller_ineligible",
                "Seller cannot publish.",
            )
            listing.published_at = listing.published_at or utcnow()
            if listing.is_paused:
                status = "paused"
        listing.status = status
        listing.revision += 1
        await self.session.flush()
        if status == "live":
            await FeedService(self.session).project(
                await self.detail(listing_id), listing.latitude, listing.longitude
            )
        else:
            await FeedService(self.session).remove(listing_id)
        await emit(
            self.session,
            "listing.status",
            {"listing_id": str(listing.id), "status": status, "user_id": str(listing.seller_id)},
        )

    async def sold(self, listing_id: UUID, user: UUID) -> ListingView:
        """Mark an owned live listing sold and remove its candidate projection."""
        from app.modules.feed.service import FeedService

        listing = await self.owned(listing_id, user, lock=True)
        require(
            listing.status in {"live", "paused", "sold"},
            409,
            "invalid_state",
            "Only published listings can be marked sold.",
        )
        listing.status, listing.sold_at = "sold", listing.sold_at or utcnow()
        listing.revision += 1
        await FeedService(self.session).remove(listing_id)
        await emit(
            self.session,
            "listing.status",
            {"listing_id": str(listing.id), "status": "sold", "user_id": str(user)},
        )
        return await self.detail(listing_id, user)

    async def save(self, listing_id: UUID, user: UUID, saved: bool) -> None:
        """Set saved state idempotently."""
        await self.detail(listing_id, user)
        if saved:
            await self.session.execute(
                insert(Save).values(user_id=user, listing_id=listing_id).on_conflict_do_nothing()
            )
        else:
            row = await self.session.get(Save, (user, listing_id))
            if row:
                await self.session.delete(row)

    async def visible_ids(self, ids: list[UUID]) -> set[UUID]:
        """Supply current live IDs for projection safety checks."""
        return await self.repo.visible_ids(ids)

    async def is_saved(self, user: UUID, listing: UUID) -> bool:
        """Expose saved state without leaking our repository."""
        return await self.repo.saved(user, listing)

    async def moderation_context(self, listing_id: UUID) -> tuple[str, int]:
        """Supply text and its edit revision to the scanner without exposing storage details."""
        listing = await self.repo.get(listing_id)
        require(listing, 404, "listing_missing", "Listing not found.")
        assert listing is not None
        return f"{listing.title}\n{listing.description}", listing.revision

    async def conversation_facts(self, listing_id: UUID) -> tuple[str, UUID]:
        """Supply minimal facts for existing conversations even after a removal."""
        listing = await self.repo.get(listing_id)
        require(listing, 404, "listing_missing", "Listing not found.")
        assert listing is not None
        return listing.title, listing.seller_id

    async def saved_page(self, user: UUID, cursor: str | None) -> ListingPage:
        """Return saved listings using keyset pagination."""
        after = UUID(decode_cursor(cursor)["id"]) if cursor else None
        ids = await self.repo.saved_ids(user, after, 21)
        items = []
        from app.core.errors import DomainError

        for listing_id in ids[:20]:
            try:
                items.append(await self.detail(listing_id, user))
            except DomainError:
                continue
        return ListingPage(
            items=items, next_cursor=encode_cursor({"id": str(ids[19])}) if len(ids) > 20 else None
        )

    async def seller_detail(self, listing_id: UUID, user: UUID) -> SellerListingView:
        """Expose draft and upload information exclusively to the owning seller."""
        from app.modules.media.service import MediaService

        listing = await self.owned(listing_id, user)
        view = await self.detail(listing_id, user)
        return SellerListingView(
            **view.model_dump(),
            revision=listing.revision,
            is_paused=listing.is_paused,
            latitude=listing.latitude,
            longitude=listing.longitude,
            created_at=listing.created_at,
            media=await MediaService(self.session).owner_info(listing.id),
        )

    async def mine(self, user: UUID, cursor: str | None, status: str | None) -> SellerListingPage:
        """List owned adverts, including unpublished drafts, with an identity-bound keyset."""
        after = None
        if cursor:
            state = decode_cursor(cursor)
            require(
                state.get("scope") == "seller"
                and state.get("user") == str(user)
                and state.get("status") == status,
                400,
                "cursor_mismatch",
                "Restart your listing list after changing filters.",
            )
            after = (cursor_time(state["time"]), UUID(state["id"]))
        rows = await self.repo.owner_page(user, status, after)
        last = rows[19] if len(rows) > 20 else None
        return SellerListingPage(
            items=[await self.seller_detail(row.id, user) for row in rows[:20]],
            next_cursor=encode_cursor(
                {
                    "scope": "seller",
                    "user": str(user),
                    "status": status,
                    "time": last.created_at.isoformat(),
                    "id": str(last.id),
                }
            )
            if last
            else None,
        )

    async def update(self, listing_id: UUID, user: UUID, data: ListingUpdate) -> SellerListingView:
        """Edit an owned advert without overwriting another tab or bypassing moderation."""
        from app.modules.feed.service import FeedService
        from app.modules.media.service import MediaService
        from app.modules.moderation.service import ModerationService

        seller = await UserService(self.session).active(user)
        require(
            seller.verified_at and seller.adult_declared,
            403,
            "seller_ineligible",
            "Verify your phone and confirm you are 18+ before editing an advert.",
        )
        listing = await self.owned(listing_id, user, lock=True)
        require(
            listing.status not in {"sold", "removed"},
            409,
            "listing_closed",
            "Closed adverts cannot be edited.",
        )
        require(
            listing.revision == data.revision,
            409,
            "listing_changed",
            "This advert changed. Reload its latest details before saving.",
        )
        await self.repo.edit(
            listing, data.model_dump(exclude={"car", "revision"}), data.car.model_dump()
        )
        listing.revision += 1
        review = await ModerationService(self.session).scan_listing(listing.id, False)
        if review and listing.status in {"live", "paused"}:
            await MediaService(self.session).require_review(listing.id)
        elif listing.status == "live":
            await FeedService(self.session).project(
                await self.detail(listing.id), listing.latitude, listing.longitude
            )
        await emit(
            self.session,
            "listing.status",
            {"listing_id": str(listing.id), "status": listing.status, "user_id": str(user)},
        )
        return await self.seller_detail(listing.id, user)

    async def pause(
        self, listing_id: UUID, user: UUID, revision: int, paused: bool
    ) -> SellerListingView:
        """Pause or restore a reviewed advert, keeping feed visibility transactional."""
        from app.modules.media.service import MediaService

        listing = await self.owned(listing_id, user, lock=True)
        require(
            listing.revision == revision,
            409,
            "listing_changed",
            "This advert changed. Refresh before trying again.",
        )
        require(
            listing.status in {"live", "paused"},
            409,
            "invalid_state",
            "Only published adverts can be paused or resumed.",
        )
        media = await MediaService(self.session).playable(listing.id)
        require(media, 409, "media_unavailable", "Approved video is required to publish.")
        listing.is_paused = paused
        await self.media_state(listing.id, "paused" if paused else "live")
        return await self.seller_detail(listing.id, user)

    async def lock_for_media(self, listing_id: UUID) -> Listing:
        """Serialize a media finalization with seller lifecycle changes."""
        listing = await self.repo.get(listing_id, lock=True)
        require(listing, 404, "listing_missing", "Listing not found.")
        assert listing is not None
        return listing
