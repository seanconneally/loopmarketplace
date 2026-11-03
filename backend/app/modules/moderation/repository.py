from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.moderation.models import Block, Report


class ModerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def blocked(self, first: UUID, second: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(Block.id)
                .where(
                    or_(
                        and_(Block.blocker_id == first, Block.blocked_id == second),
                        and_(Block.blocker_id == second, Block.blocked_id == first),
                    )
                )
                .limit(1)
            )
        )

    async def blocked_peers(self, user: UUID, peers: set[UUID]) -> set[UUID]:
        rows = await self.session.execute(
            select(Block.blocker_id, Block.blocked_id).where(
                or_(
                    and_(Block.blocker_id == user, Block.blocked_id.in_(peers)),
                    and_(Block.blocked_id == user, Block.blocker_id.in_(peers)),
                )
            )
        )
        return {second if first == user else first for first, second in rows}

    async def reports(self, after: UUID | None) -> list[Report]:
        query = select(Report).where(Report.status == "open")
        if after:
            query = query.where(Report.id < after)
        return list(await self.session.scalars(query.order_by(Report.id.desc()).limit(21)))
