from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def deliver(self, event_id: UUID, payload: dict[str, Any]) -> None:
        """Store the local in-app notification once; no outbound provider is simulated as sent."""
        from app.modules.viewings.service import ViewingService

        if payload["kind"] == "viewing_reminder" and not await ViewingService(
            self.session
        ).reminder_valid(UUID(payload["viewing_id"]), int(payload["revision"])):
            return
        await self.session.execute(
            insert(Notification)
            .values(
                user_id=UUID(payload["user_id"]),
                event_id=event_id,
                kind=payload["kind"],
                payload=payload,
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
