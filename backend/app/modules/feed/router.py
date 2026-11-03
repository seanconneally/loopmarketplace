from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import OptionalUser, Session
from app.modules.feed.schemas import FeedFilters, FeedPage
from app.modules.feed.service import FeedService

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=FeedPage)
async def feed(
    session: Session,
    user: OptionalUser,
    filters: Annotated[FeedFilters, Depends()],
    cursor: str | None = None,
) -> FeedPage:
    return await FeedService(session).page(filters, user, cursor)
