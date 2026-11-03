from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import OptionalUser, Session
from app.modules.feed.schemas import FeedFilters, FeedOptions, FeedPage, FeedRequest
from app.modules.feed.service import FeedService

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=FeedPage)
async def feed(
    session: Session,
    user: OptionalUser,
    filters: Annotated[FeedRequest, Query()],
) -> FeedPage:
    return await FeedService(session).page(
        FeedFilters.model_validate(filters.model_dump(exclude={"cursor"})), user, filters.cursor
    )


@router.get("/options", response_model=FeedOptions)
async def options(session: Session) -> FeedOptions:
    return await FeedService(session).options()
