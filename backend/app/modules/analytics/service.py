from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import require
from app.core.outbox import emit
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import EventBatch
from app.modules.users.service import UserService


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, AnalyticsRepository(session)

    async def append(self, user: UUID, data: EventBatch) -> None:
        """Store deduplicated events only after checking current opt-in consent."""
        require(
            (await UserService(self.session).active(user)).analytics_consent,
            403,
            "consent_required",
            "Enable optional analytics first.",
        )
        await self.repo.append(user, data.events)
        await emit(
            self.session,
            "analytics.received",
            {
                "user_id": str(user),
                "seen_ids": [
                    str(event.listing_id)
                    for event in data.events
                    if event.event_type == "impression"
                ],
            },
        )
