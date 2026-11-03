from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity


class Report(Identity, Base):
    __tablename__ = "reports"
    reporter_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[UUID]
    reason: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="open")
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    __table_args__ = (Index("ix_reports_queue", "status", "created_at", "id"),)


class Block(Identity, Base):
    __tablename__ = "blocks"
    blocker_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    blocked_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id"),
        Index("ix_blocks_reverse", "blocked_id", "blocker_id"),
    )


class ModerationAction(Identity, Base):
    __tablename__ = "moderation_actions"
    moderator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[UUID]
    action: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(1000))
    appeal_status: Mapped[str | None] = mapped_column(String(20))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
