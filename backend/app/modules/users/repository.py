from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import Dealer, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def by_phone(self, phone: str) -> User | None:
        return cast(User | None, await self.session.scalar(select(User).where(User.phone == phone)))

    async def dealer(self, user_id: UUID) -> Dealer | None:
        return cast(
            Dealer | None,
            await self.session.scalar(select(Dealer).where(Dealer.user_id == user_id)),
        )
