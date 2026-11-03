from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity


class Conversation(Identity, Base):
    __tablename__ = "conversations"
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    buyer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("listing_id", "buyer_id"),
        Index("ix_conversation_buyer", "buyer_id", "created_at"),
        Index("ix_conversation_seller", "seller_id", "created_at"),
    )


class Message(Identity, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(4000))
    message_type: Mapped[str] = mapped_column(String(20), default="text")
    viewing_id: Mapped[UUID | None] = mapped_column(ForeignKey("viewings.id"))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("conversation_id", "sender_id", "idempotency_key"),
        Index("ix_messages_history", "conversation_id", "created_at", "id"),
    )
