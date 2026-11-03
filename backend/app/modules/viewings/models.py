from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity


class Viewing(Identity, Base):
    __tablename__ = "viewings"
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"))
    proposed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    place: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    revision: Mapped[int] = mapped_column(default=1)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("conversation_id", "idempotency_key"),
        CheckConstraint(
            "status in ('proposed','accepted','declined','cancelled')", name="valid_status"
        ),
        Index("ix_viewings_conversation", "conversation_id", "id"),
        Index(
            "ix_viewings_reminder", "status", "starts_at", postgresql_where=reminded_at.is_(None)
        ),
    )
