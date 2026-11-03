import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import DomainError, require
from app.core.redis import client, command, rate_limit
from app.modules.auth.models import RefreshSession
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import AuthView, ChallengeView
from app.modules.users.schemas import UserView
from app.modules.users.service import UserService


def digest(value: str) -> str:
    return hmac.new(settings().jwt_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, AuthRepository(session)
        self.users = UserService(session)

    async def challenge(self, phone: str, ip: str) -> ChallengeView:
        """Create a bounded development OTP challenge, without logging the phone."""
        require(await rate_limit(f"otp-ip:{ip}", 10, 600), 429, "rate_limited", "Try later.")
        require(
            await rate_limit(f"otp-phone:{digest(phone)}", 3, 600),
            429,
            "rate_limited",
            "Try later.",
        )
        code = (
            "123456" if settings().app_env != "production" else f"{secrets.randbelow(1000000):06}"
        )
        await client.set(f"otp:{digest(phone)}", digest(f"{phone}:{code}"), ex=300)
        return ChallengeView(message="Development only: SMS is simulated.", development_code=code)

    async def verify(self, phone: str, code: str) -> tuple[AuthView, str]:
        """Consume a valid OTP atomically and establish a rotating session."""
        key = digest(phone)
        require(
            await rate_limit(f"otp-attempt:{key}", 5, 300),
            429,
            "rate_limited",
            "Too many attempts.",
        )
        consumed = await command(
            "EVAL",
            "if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) else return 0 end",
            1,
            f"otp:{key}",
            digest(f"{phone}:{code}"),
        )
        require(consumed, 401, "invalid_otp", "Code expired or incorrect.")
        user = await self.users.verify_phone(phone)
        return await self._issue(user.id, uuid4())

    async def _issue(self, user_id: UUID, family: UUID) -> tuple[AuthView, str]:
        refresh = secrets.token_urlsafe(48)
        now = utcnow()
        self.session.add(
            RefreshSession(
                user_id=user_id,
                family_id=family,
                token_hash=digest(refresh),
                expires_at=now + timedelta(days=settings().refresh_days),
            )
        )
        token = jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(family),
                "jti": str(uuid4()),
                "iat": now,
                "exp": now + timedelta(minutes=settings().access_minutes),
                "iss": "motorloop",
                "aud": "motorloop-web",
            },
            settings().jwt_secret,
            algorithm="HS256",
        )
        await self.session.flush()
        return AuthView(
            access_token=token, user=UserView.model_validate(await self.users.active(user_id))
        ), refresh

    async def refresh(self, token: str) -> tuple[AuthView, str]:
        """Rotate a refresh token and revoke the entire family on reuse."""
        row = await self.repo.locked_token(digest(token))
        require(row, 401, "invalid_session", "Sign in again.")
        assert row is not None
        if row.used_at or row.revoked:
            await self.repo.revoke_family(row.family_id)
            await self.session.commit()  # Revocation must survive the error response rollback.
            raise DomainError(401, "session_reused", "Session revoked. Sign in again.")
        require(row.expires_at > utcnow(), 401, "expired_session", "Sign in again.")
        row.used_at = utcnow()
        return await self._issue(row.user_id, row.family_id)

    async def authenticate(self, token: str) -> tuple[UUID, UUID]:
        """Check signed token and authoritative account/session state."""
        try:
            claims = jwt.decode(
                token,
                settings().jwt_secret,
                algorithms=["HS256"],
                issuer="motorloop",
                audience="motorloop-web",
                options={"require": ["exp", "iat", "sub", "sid", "jti"]},
            )
            user_id, family = UUID(claims["sub"]), UUID(claims["sid"])
        except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
            raise DomainError(401, "invalid_token", "Sign in again.") from exc
        await self.users.active(user_id)
        require(
            await self.repo.valid_family(user_id, family), 401, "invalid_session", "Sign in again."
        )
        return user_id, family

    async def logout(self, token: str) -> None:
        """Revoke this refresh family; access validation observes it immediately."""
        row = await self.repo.locked_token(digest(token))
        if row:
            await self.repo.revoke_family(row.family_id)

    async def ticket(self, user_id: UUID, family: UUID) -> str:
        """Mint a single-use, thirty-second WebSocket ticket."""
        ticket = secrets.token_urlsafe(32)
        await client.set(
            f"ws-ticket:{digest(ticket)}", json.dumps([str(user_id), str(family)]), ex=30
        )
        return ticket
