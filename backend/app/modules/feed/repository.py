from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, and_, cast, delete, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feed.models import Candidate
from app.modules.feed.schemas import FeedFilters


class FeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def candidates(
        self,
        filters: FeedFilters,
        limit: int = 150,
        after: tuple[datetime, UUID] | None = None,
        after_price: int | None = None,
        ids: list[UUID] | None = None,
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
        if ids is not None:
            query = query.where(Candidate.listing_id.in_(ids))
        car = Candidate.public_data["car"]
        if filters.fuel:
            query = query.where(car["fuel"].as_string() == filters.fuel)
        if filters.transmission:
            query = query.where(car["transmission"].as_string() == filters.transmission)
        if filters.max_mileage < 3000000:
            query = query.where(cast(car["mileage_km"].as_string(), Integer) <= filters.max_mileage)
        if filters.q:
            searchable = func.lower(
                func.concat_ws(
                    " ",
                    Candidate.public_data["title"].as_string(),
                    Candidate.make,
                    car["model"].as_string(),
                    Candidate.public_data["area"].as_string(),
                    car["fuel"].as_string(),
                    car["transmission"].as_string(),
                    Candidate.year,
                )
            )
            for word in filters.q.split():
                query = query.where(searchable.contains(word, autoescape=True))
        if filters.sort in {"price_asc", "price_desc"}:
            query = query.order_by(
                Candidate.price_cents.asc()
                if filters.sort == "price_asc"
                else Candidate.price_cents.desc(),
            )
        if after:
            older = tuple_(Candidate.published_at, Candidate.listing_id) < after
            if after_price is not None and filters.sort in {"price_asc", "price_desc"}:
                price_order = (
                    Candidate.price_cents > after_price
                    if filters.sort == "price_asc"
                    else Candidate.price_cents < after_price
                )
                query = query.where(
                    or_(price_order, and_(Candidate.price_cents == after_price, older))
                )
            else:
                query = query.where(older)
        return list(
            await self.session.scalars(
                query.order_by(Candidate.published_at.desc(), Candidate.listing_id.desc()).limit(
                    limit
                )
            )
        )

    async def makes(self) -> list[str]:
        return list(
            await self.session.scalars(
                select(func.min(Candidate.make))
                .where(Candidate.region_id == "ie-dublin")
                .group_by(func.lower(Candidate.make))
                .order_by(func.lower(Candidate.make))
                .limit(200)
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
