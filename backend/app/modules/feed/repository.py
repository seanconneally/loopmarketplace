from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feed.models import Candidate
from app.modules.feed.schemas import FeedFilters


class FeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def candidates(
        self, filters: FeedFilters, limit: int = 150, after: tuple[datetime, UUID] | None = None
    ) -> list[Candidate]:
        point = func.ST_SetSRID(func.ST_MakePoint(filters.longitude, filters.latitude), 4326)
        query = select(Candidate).where(
            Candidate.region_id == filters.region_id,
            func.ST_DWithin(Candidate.location, func.Geography(point), filters.radius_km * 1000),
            Candidate.price_cents.between(filters.min_price, filters.max_price),
            Candidate.year.between(filters.min_year, filters.max_year),
        )
        if filters.make:
            query = query.where(func.lower(Candidate.make) == filters.make.lower())
        if after:
            query = query.where(tuple_(Candidate.published_at, Candidate.listing_id) < after)
        return list(
            await self.session.scalars(
                query.order_by(Candidate.published_at.desc(), Candidate.listing_id.desc()).limit(
                    limit
                )
            )
        )

    async def by_ids(self, ids: list[UUID]) -> list[Candidate]:
        return list(
            await self.session.scalars(select(Candidate).where(Candidate.listing_id.in_(ids)))
        )

    async def upsert(self, values: dict[str, object]) -> None:
        statement = insert(Candidate).values(**values)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=["listing_id"],
                set_={key: value for key, value in values.items() if key != "listing_id"},
            )
        )

    async def remove(self, listing: UUID) -> None:
        await self.session.execute(delete(Candidate).where(Candidate.listing_id == listing))
