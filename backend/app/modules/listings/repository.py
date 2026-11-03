from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.listings.models import CarDetails, Listing, Save


class ListingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def titles(self, listing_ids: set[UUID]) -> dict[UUID, str]:
        return dict(
            (
                await self.session.execute(
                    select(Listing.id, Listing.title).where(Listing.id.in_(listing_ids))
                )
            )
            .tuples()
            .all()
        )

    async def get(self, listing_id: UUID, lock: bool = False) -> Listing | None:
        query = select(Listing).where(Listing.id == listing_id)
        return cast(
            Listing | None,
            await self.session.scalar(
                query.with_for_update().execution_options(populate_existing=True) if lock else query
            ),
        )

    async def by_key(self, seller: UUID, key: str) -> Listing | None:
        return cast(
            Listing | None,
            await self.session.scalar(
                select(Listing).where(Listing.seller_id == seller, Listing.idempotency_key == key)
            ),
        )

    async def car(self, listing_id: UUID) -> CarDetails | None:
        return await self.session.get(CarDetails, listing_id)

    async def saved(self, user: UUID, listing: UUID) -> bool:
        return await self.session.get(Save, (user, listing)) is not None

    async def saved_subset(self, user: UUID, ids: list[UUID]) -> set[UUID]:
        return set(
            await self.session.scalars(
                select(Save.listing_id).where(Save.user_id == user, Save.listing_id.in_(ids))
            )
        )

    async def saved_ids(self, user: UUID, after: UUID | None, limit: int) -> list[UUID]:
        query = select(Save.listing_id).where(Save.user_id == user)
        if after:
            query = query.where(Save.listing_id < after)
        return list(await self.session.scalars(query.order_by(Save.listing_id.desc()).limit(limit)))

    async def visible_ids(self, ids: list[UUID]) -> set[UUID]:
        return set(
            await self.session.scalars(
                select(Listing.id).where(Listing.id.in_(ids), Listing.status == "live")
            )
        )

    async def owner_page(
        self, seller: UUID, status: str | None, after: tuple[datetime, UUID] | None
    ) -> list[Listing]:
        query = select(Listing).where(Listing.seller_id == seller)
        if status:
            query = query.where(Listing.status == status)
        if after:
            query = query.where(tuple_(Listing.created_at, Listing.id) < after)
        return list(
            await self.session.scalars(
                query.order_by(Listing.created_at.desc(), Listing.id.desc()).limit(21)
            )
        )

    async def edit(
        self, listing: Listing, values: dict[str, object], car: dict[str, object]
    ) -> None:
        for name, value in values.items():
            setattr(listing, name, value)
        details = await self.car(listing.id)
        assert details is not None
        for name, value in car.items():
            setattr(details, name, value)
        await self.session.flush()
