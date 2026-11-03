from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.modules.auth.models import RefreshSession


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def locked_token(self, token_hash: str) -> RefreshSession | None:
        return cast(
            RefreshSession | None,
            await self.session.scalar(
                select(RefreshSession)
                .where(RefreshSession.token_hash == token_hash)
                .with_for_update()
            ),
        )

    async def revoke_family(self, family: UUID) -> None:
        await self.session.execute(
            update(RefreshSession).where(RefreshSession.family_id == family).values(revoked=True)
        )

    async def valid_family(self, user_id: UUID, family: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(RefreshSession.id)
                .where(
                    RefreshSession.user_id == user_id,
                    RefreshSession.family_id == family,
                    RefreshSession.revoked.is_(False),
                    RefreshSession.used_at.is_(None),
                    RefreshSession.expires_at > utcnow(),
                )
                .limit(1)
            )
        )
