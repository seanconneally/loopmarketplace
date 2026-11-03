from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.modules.analytics.models import Event
from app.modules.analytics.schemas import EventInput


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, user: UUID, events: list[EventInput]) -> None:
        await self.session.execute(
            insert(Event)
            .values(
                [
                    {
                        "user_id": user,
                        **event.model_dump(exclude={"occurred_at"}),
                        "created_at": min(event.occurred_at or utcnow(), utcnow()),
                    }
                    for event in events
                ]
            )
            .on_conflict_do_nothing()
        )

    async def recent(self, user: UUID, since: datetime) -> list[Event]:
        return list(
            await self.session.scalars(
                select(Event)
                .where(
                    Event.user_id == user,
                    Event.created_at > since,
                )
                .order_by(Event.created_at.desc(), Event.id.desc())
                .limit(200)
            )
        )

    async def remove_dismissal(self, user: UUID, listing: UUID) -> None:
        await self.session.execute(
            delete(Event).where(
                Event.user_id == user,
                Event.listing_id == listing,
                Event.event_type == "not_interested",
            )
        )
