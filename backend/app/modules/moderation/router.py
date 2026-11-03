from uuid import UUID

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, IdempotencyKey, Session
from app.modules.moderation.schemas import (
    ActionInput,
    BlockInput,
    ReportInput,
    ReportPage,
    ReportView,
)
from app.modules.moderation.service import ModerationService

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.post("/reports", response_model=ReportView, status_code=201)
async def report(
    data: ReportInput, session: Session, user: CurrentUser, key: IdempotencyKey
) -> ReportView:
    return await ModerationService(session).report(user, data, key)


@router.put("/blocks", status_code=204)
async def block(data: BlockInput, session: Session, user: CurrentUser) -> None:
    await ModerationService(session).set_block(user, data.user_id, True)


@router.delete("/blocks/{target_id}", status_code=204)
async def unblock(target_id: UUID, session: Session, user: CurrentUser) -> None:
    await ModerationService(session).set_block(user, target_id, False)


@router.get("/queue", response_model=ReportPage)
async def queue(session: Session, user: CurrentUser, cursor: str | None = None) -> ReportPage:
    return await ModerationService(session).queue(user, cursor)


@router.post("/actions", status_code=204)
async def action(
    data: ActionInput, session: Session, user: CurrentUser, key: IdempotencyKey
) -> None:
    await ModerationService(session).act(user, data, key)
