from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import Event
from app.modules.analytics.schemas import EventInput


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, user: UUID, events: list[EventInput]) -> None:
        await self.session.execute(
            insert(Event)
            .values([{"user_id": user, **event.model_dump()} for event in events])
            .on_conflict_do_nothing()
        )
