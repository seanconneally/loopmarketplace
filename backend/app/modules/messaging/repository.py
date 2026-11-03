from uuid import UUID

from sqlalchemy import or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.paging import cursor_time, decode_cursor
from app.modules.messaging.models import Conversation, Message


class MessagingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def conversation(self, conversation: UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation)

    async def conversations(self, user: UUID, after: UUID | None) -> list[Conversation]:
        query = select(Conversation).where(
            or_(Conversation.buyer_id == user, Conversation.seller_id == user)
        )
        if after:
            query = query.where(Conversation.id < after)
        return list(await self.session.scalars(query.order_by(Conversation.id.desc()).limit(21)))

    async def messages(self, conversation: UUID, cursor: str | None) -> list[Message]:
        query = select(Message).where(Message.conversation_id == conversation)
        if cursor:
            value = decode_cursor(cursor)
            query = query.where(
                tuple_(Message.created_at, Message.id)
                < (cursor_time(value["time"]), UUID(value["id"]))
            )
        return list(
            await self.session.scalars(
                query.order_by(Message.created_at.desc(), Message.id.desc()).limit(51)
            )
        )
