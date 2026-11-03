from fastapi import APIRouter

from app.core.dependencies import CurrentUser, Session
from app.modules.analytics.schemas import EventBatch
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events", status_code=204)
async def events(data: EventBatch, session: Session, user: CurrentUser) -> None:
    await AnalyticsService(session).append(user, data)
