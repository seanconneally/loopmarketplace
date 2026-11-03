from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.viewings.models import Viewing


class ViewingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def locked(self, viewing_id: UUID) -> Viewing | None:
        return cast(
            Viewing | None,
            await self.session.scalar(
                select(Viewing).where(Viewing.id == viewing_id).with_for_update()
            ),
        )

    async def page(self, conversation: UUID, after: UUID | None) -> list[Viewing]:
        query = select(Viewing).where(Viewing.conversation_id == conversation)
        if after:
            query = query.where(Viewing.id < after)
        return list(await self.session.scalars(query.order_by(Viewing.id.desc()).limit(21)))
