from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import require
from app.core.outbox import emit
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import ProfileUpdate, SellerView, UserView


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, UserRepository(session)

    async def active(self, user_id: UUID) -> User:
        """Return an active user, refusing suspended or deleted identities."""
        user = await self.repo.get(user_id)
        require(
            user and user.status == "active", 403, "account_unavailable", "Account unavailable."
        )
        assert user is not None
        return user

    async def verify_phone(self, phone: str) -> User:
        """Create or verify a phone identity after successful OTP consumption."""
        user = await self.repo.by_phone(phone)
        if user is None:
            user = User(phone=phone, verified_at=utcnow())
            self.session.add(user)
            await self.session.flush()
        require(user.status == "active", 403, "account_unavailable", "Account unavailable.")
        user.verified_at = utcnow()
        return user

    async def seller(self, user_id: UUID) -> SellerView:
        """Expose only public seller facts, never contact data."""
        user = await self.active(user_id)
        dealer = await self.repo.dealer(user_id)
        return SellerView(
            id=user.id, name=user.name, dealer_verified=bool(dealer and dealer.verified_at)
        )

    async def update(self, user_id: UUID, data: ProfileUpdate) -> UserView:
        """Update profile declarations and consent explicitly."""
        user = await self.active(user_id)
        if user.analytics_consent and not data.analytics_consent:
            await emit(self.session, "analytics.withdrawn", {"user_id": str(user_id)})
        user.name, user.adult_declared = data.name, data.adult_declared
        user.analytics_consent = data.analytics_consent
        await self.session.flush()
        return UserView.model_validate(user)

    async def suspend(self, user_id: UUID) -> None:
        """Suspend an account as directed by an authorized moderation action."""
        (await self.active(user_id)).status = "suspended"

    async def dealer_verified(self, user_id: UUID) -> bool:
        """Expose business verification without allowing another module's table queries."""
        dealer = await self.repo.dealer(user_id)
        return bool(dealer and dealer.verified_at)
