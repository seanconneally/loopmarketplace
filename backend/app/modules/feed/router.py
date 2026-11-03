from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, OptionalUser, Session
from app.modules.feed.schemas import FeedFeedback, FeedFilters, FeedOptions, FeedPage, FeedRequest
from app.modules.feed.service import FeedService

router = APIRouter(prefix="/feed", tags=["feed"])


@router.put("/feedback", status_code=204)
async def feedback(data: FeedFeedback, session: Session, user: CurrentUser) -> None:
    await FeedService(session).dismiss(user, data.listing_id)


@router.delete("/feedback/{listing_id}", status_code=204)
async def undo_feedback(listing_id: UUID, session: Session, user: CurrentUser) -> None:
    await FeedService(session).undo_dismiss(user, listing_id)


@router.delete("/preferences", status_code=204)
async def reset_preferences(session: Session, user: CurrentUser) -> None:
    await FeedService(session).reset_preferences(user)


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
