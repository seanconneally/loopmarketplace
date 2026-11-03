from uuid import UUID

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, IdempotencyKey, Session
from app.modules.messaging.schemas import (
    ConversationInput,
    ConversationPage,
    ConversationView,
    MessageInput,
    MessagePage,
    MessageView,
    ReadInput,
)
from app.modules.messaging.service import MessagingService

router = APIRouter(prefix="/conversations", tags=["messaging"])


@router.post("", response_model=ConversationView, status_code=201)
async def start(
    data: ConversationInput, session: Session, user: CurrentUser, key: IdempotencyKey
) -> ConversationView:
    return await MessagingService(session).start(data.listing_id, user)


@router.get("", response_model=ConversationPage)
async def page(session: Session, user: CurrentUser, cursor: str | None = None) -> ConversationPage:
    return await MessagingService(session).page(user, cursor)


@router.get("/{conversation_id}/messages", response_model=MessagePage)
async def history(
    conversation_id: UUID, session: Session, user: CurrentUser, cursor: str | None = None
) -> MessagePage:
    return await MessagingService(session).history(conversation_id, user, cursor)


@router.post("/{conversation_id}/messages", response_model=MessageView, status_code=201)
async def send(
    conversation_id: UUID,
    data: MessageInput,
    session: Session,
    user: CurrentUser,
    key: IdempotencyKey,
) -> MessageView:
    return await MessagingService(session).send(conversation_id, user, data.body, key)


@router.put("/{conversation_id}/read", status_code=204)
async def read(conversation_id: UUID, data: ReadInput, session: Session, user: CurrentUser) -> None:
    await MessagingService(session).read(conversation_id, user, data.message_id)
