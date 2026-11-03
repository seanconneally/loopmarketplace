from datetime import datetime
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import require
from app.core.outbox import emit
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import EventBatch, EventInput, InterestEvent
from app.modules.users.service import UserService


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, AnalyticsRepository(session)

    async def recent(self, user: UUID, since: datetime) -> list[InterestEvent]:
        """Return bounded interest signals only while the member currently consents."""
        if not (await UserService(self.session).active(user)).analytics_consent:
            return []
        return [InterestEvent.model_validate(row) for row in await self.repo.recent(user, since)]

    async def undo_dismissal(self, user: UUID, listing: UUID) -> None:
        await self.repo.remove_dismissal(user, listing)

    async def action(
        self, user: UUID, listing: UUID, action: Literal["save", "message", "not_interested"]
    ) -> None:
        """Record an authorized marketplace action at most once per listing/type/day."""
        if not (await UserService(self.session).active(user)).analytics_consent:
            return
        event = EventInput(
            client_event_id=uuid5(
                NAMESPACE_URL, f"motorloop:{user}:{listing}:{action}:{utcnow().date()}"
            ),
            listing_id=listing,
            event_type=action,
            value=1,
        )
        await self.repo.append(user, [event])

    async def append(self, user: UUID, data: EventBatch) -> None:
        """Store deduplicated events only after checking current opt-in consent."""
        require(
            (await UserService(self.session).active(user)).analytics_consent,
            403,
            "consent_required",
            "Enable optional analytics first.",
        )
        from app.modules.feed.repository import FeedRepository
        from app.modules.listings.service import ListingService

        cutoff = await FeedRepository(self.session).cutoff(user)
        visible = await ListingService(self.session).visible_ids(
            [event.listing_id for event in data.events]
        )
        accepted = [
            event
            for event in data.events
            if (cutoff is None or (event.occurred_at or utcnow()) > cutoff)
            and event.listing_id in visible
            and event.event_type in {"impression", "watch", "completion", "replay"}
        ]
        if not accepted:
            return
        await self.repo.append(user, accepted)
        await emit(
            self.session,
            "analytics.received",
            {
                "user_id": str(user),
                "seen_ids": [
                    str(event.listing_id) for event in accepted if event.event_type == "impression"
                ],
            },
        )
