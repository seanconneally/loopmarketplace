from uuid import UUID

from sqlalchemy import select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import require
from app.core.outbox import emit
from app.core.paging import decode_cursor, encode_cursor
from app.modules.listings.service import ListingService
from app.modules.messaging.models import Conversation, Message
from app.modules.messaging.repository import MessagingRepository
from app.modules.messaging.schemas import (
    ConversationPage,
    ConversationView,
    MessagePage,
    MessageView,
)
from app.modules.moderation.service import ModerationService, scam_warnings
from app.modules.users.service import UserService


class MessagingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, MessagingRepository(session)

    async def member(self, conversation_id: UUID, user: UUID) -> Conversation:
        """Authorize membership, verification, current identities and symmetric blocks."""
        conversation = await self.repo.conversation(conversation_id)
        require(
            conversation and user in {conversation.buyer_id, conversation.seller_id},
            404,
            "conversation_missing",
            "Conversation not found.",
        )
        assert conversation is not None
        require(
            (await UserService(self.session).active(user)).verified_at,
            403,
            "verification_required",
            "Verify your phone.",
        )
        other = conversation.seller_id if user == conversation.buyer_id else conversation.buyer_id
        await UserService(self.session).active(other)
        require(
            not await ModerationService(self.session).blocked(user, other),
            403,
            "blocked",
            "This conversation is unavailable.",
        )
        return conversation

    async def start(self, listing_id: UUID, user: UUID) -> ConversationView:
        """Create the unique listing/buyer conversation or return the existing one."""
        listing = await ListingService(self.session).detail(listing_id, user)
        require(
            listing.status == "live",
            409,
            "listing_unavailable",
            "This listing is no longer available.",
        )
        require(user != listing.seller.id, 422, "own_listing", "You cannot message yourself.")
        await self.session.execute(
            insert(Conversation)
            .values(listing_id=listing_id, buyer_id=user, seller_id=listing.seller.id)
            .on_conflict_do_nothing(index_elements=["listing_id", "buyer_id"])
        )
        conversation = await self.session.scalar(
            select(Conversation).where(
                Conversation.listing_id == listing_id, Conversation.buyer_id == user
            )
        )
        assert conversation is not None
        await self.member(conversation.id, user)
        return await self._view(conversation, user)

    async def _view(self, conversation: Conversation, user: UUID) -> ConversationView:
        result = ConversationView.model_validate(conversation)
        result.listing_title = (
            await ListingService(self.session).conversation_facts(conversation.listing_id)
        )[0]
        other = conversation.seller_id if user == conversation.buyer_id else conversation.buyer_id
        result.other_name = (await UserService(self.session).active(other)).name
        return result

    async def page(self, user: UUID, cursor: str | None) -> ConversationPage:
        """List the user's conversation summaries with cursor pagination."""
        after = UUID(decode_cursor(cursor)["id"]) if cursor else None
        rows = await self.repo.conversations(user, after)
        caller = await UserService(self.session).active(user)
        require(caller.verified_at, 403, "verification_required", "Verify your phone.")
        page = rows[:20]
        peers = {row.seller_id if row.buyer_id == user else row.buyer_id for row in page}
        names = await UserService(self.session).active_names(peers)
        blocked = await ModerationService(self.session).blocked_peers(user, peers)
        titles = await ListingService(self.session).conversation_titles(
            {row.listing_id for row in page}
        )
        items = []
        for row in page:
            peer = row.seller_id if row.buyer_id == user else row.buyer_id
            if peer not in names or peer in blocked:
                continue
            result = ConversationView.model_validate(row)
            result.other_name, result.listing_title = (
                names[peer],
                titles.get(row.listing_id, "Listing"),
            )
            items.append(result)
        return ConversationPage(
            items=items,
            next_cursor=encode_cursor({"id": str(rows[19].id)}) if len(rows) > 20 else None,
        )

    async def history(self, conversation: UUID, user: UUID, cursor: str | None) -> MessagePage:
        """Replay persisted messages after reconnect, independently of Redis delivery."""
        await self.member(conversation, user)
        rows = await self.repo.messages(conversation, cursor)
        last = rows[49] if len(rows) > 50 else None
        return MessagePage(
            items=[MessageView.model_validate(row) for row in reversed(rows[:50])],
            next_cursor=encode_cursor({"time": last.created_at.isoformat(), "id": str(last.id)})
            if last
            else None,
        )

    async def send(
        self, conversation_id: UUID, user: UUID, body: str, key: str, viewing_id: UUID | None = None
    ) -> MessageView:
        """Persist once before fan-out, with recipient-visible scam warnings."""
        conversation = await self.member(conversation_id, user)
        require(bool(body.strip()), 422, "empty_message", "Enter a message.")
        result = await self.session.execute(
            insert(Message)
            .values(
                conversation_id=conversation_id,
                sender_id=user,
                body=body,
                warnings=scam_warnings(body),
                idempotency_key=key,
                message_type="viewing" if viewing_id else "text",
                viewing_id=viewing_id,
            )
            .on_conflict_do_nothing(
                index_elements=["conversation_id", "sender_id", "idempotency_key"]
            )
            .returning(Message.id)
        )
        new_id = result.scalar_one_or_none()
        row = await self.session.scalar(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.sender_id == user,
                Message.idempotency_key == key,
            )
        )
        assert row is not None
        require(
            row.body == body and row.viewing_id == viewing_id,
            409,
            "idempotency_conflict",
            "This key belongs to another message.",
        )
        view = MessageView.model_validate(row)
        if new_id:
            conversation.last_message_at = row.created_at
            await emit(
                self.session,
                "message.created",
                {
                    "conversation_id": str(conversation_id),
                    "message": view.model_dump(mode="json"),
                    "recipients": [str(conversation.buyer_id), str(conversation.seller_id)],
                },
            )
            await emit(
                self.session,
                "notification.requested",
                {
                    "user_id": str(
                        conversation.seller_id
                        if user == conversation.buyer_id
                        else conversation.buyer_id
                    ),
                    "kind": "message",
                    "conversation_id": str(conversation_id),
                    "message_id": str(row.id),
                },
            )
        return view

    async def read(self, conversation_id: UUID, user: UUID, message_id: UUID) -> None:
        """Advance read receipts to a message the caller is authorized to see."""
        conversation = await self.member(conversation_id, user)
        target = await self.session.get(Message, message_id)
        require(
            target and target.conversation_id == conversation_id,
            404,
            "message_missing",
            "Message not found.",
        )
        assert target is not None
        now = utcnow()
        await self.session.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != user,
                Message.read_at.is_(None),
                tuple_(Message.created_at, Message.id) <= (target.created_at, target.id),
            )
            .values(read_at=now)
        )
        await emit(
            self.session,
            "message.read",
            {
                "conversation_id": str(conversation_id),
                "reader_id": str(user),
                "message_id": str(message_id),
                "read_at": now.isoformat(),
                "recipients": [str(conversation.buyer_id), str(conversation.seller_id)],
            },
        )

    async def message_for_report(self, message_id: UUID, user: UUID) -> None:
        """Authorize reports against messages without exposing unrelated conversations."""
        row = await self.session.get(Message, message_id)
        require(row, 404, "message_missing", "Message not found.")
        assert row is not None
        await self.member(row.conversation_id, user)
