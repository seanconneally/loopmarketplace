from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session, utcnow
from app.core.errors import require
from app.core.redis import rate_limit
from app.modules.auth.service import AuthService
from app.modules.users.service import UserService

Session = Annotated[AsyncSession, Depends(get_session)]
bearer = HTTPBearer(auto_error=False)


async def identity(
    request: Request,
    session: Session,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UUID:
    require(credentials, 401, "authentication_required", "Sign in to continue.")
    assert credentials is not None
    user_id, _ = await AuthService(session).authenticate(credentials.credentials)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        member = await UserService(session).active(user_id)
        limit = 20 if member.created_at > utcnow() - timedelta(days=1) else 120
        require(
            await rate_limit(f"user-mutations:{user_id}", limit),
            429,
            "rate_limited",
            "Please slow down and try again shortly.",
        )
    return user_id


CurrentUser = Annotated[UUID, Depends(identity)]


async def optional_identity(
    session: Session, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> UUID | None:
    if credentials is None:
        return None
    user_id, _ = await AuthService(session).authenticate(credentials.credentials)
    return user_id


OptionalUser = Annotated[UUID | None, Depends(optional_identity)]


def same_origin(request: Request) -> None:
    require(
        request.headers.get("origin") == settings().public_origin,
        403,
        "invalid_origin",
        "This request must come from the application.",
    )


def idempotency_key(
    value: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
) -> str:
    return value


IdempotencyKey = Annotated[str, Depends(idempotency_key)]
