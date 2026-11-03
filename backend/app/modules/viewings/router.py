from uuid import UUID

from fastapi import APIRouter, Response

from app.core.dependencies import CurrentUser, IdempotencyKey, Session
from app.modules.viewings.schemas import ViewingInput, ViewingPage, ViewingResponse, ViewingView
from app.modules.viewings.service import ViewingService

router = APIRouter(prefix="/viewings", tags=["viewings"])


@router.post("", response_model=ViewingView, status_code=201)
async def create(
    data: ViewingInput, session: Session, user: CurrentUser, key: IdempotencyKey
) -> ViewingView:
    return await ViewingService(session).create(user, data, key)


@router.get("", response_model=ViewingPage)
async def page(
    conversation_id: UUID, session: Session, user: CurrentUser, cursor: str | None = None
) -> ViewingPage:
    return await ViewingService(session).page(conversation_id, user, cursor)


@router.post("/{viewing_id}/respond", response_model=ViewingView)
async def respond(
    viewing_id: UUID, data: ViewingResponse, session: Session, user: CurrentUser
) -> ViewingView:
    return await ViewingService(session).respond(viewing_id, user, data)


@router.get("/{viewing_id}/calendar")
async def calendar(viewing_id: UUID, session: Session, user: CurrentUser) -> Response:
    return Response(
        await ViewingService(session).calendar(viewing_id, user),
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="viewing.ics"',
            "Cache-Control": "no-store",
        },
    )
