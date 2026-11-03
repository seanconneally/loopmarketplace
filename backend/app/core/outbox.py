from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity, utcnow


class Outbox(Identity, Base):
    __tablename__ = "outbox"
    event_type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        Index("ix_outbox_pending", "available_at", postgresql_where=completed_at.is_(None)),
    )


class DeadLetter(Identity, Base):
    __tablename__ = "dead_letters"
    outbox_id: Mapped[UUID] = mapped_column(unique=True)
    event_type: Mapped[str] = mapped_column(String(80))
    error_code: Mapped[str] = mapped_column(String(100))
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


async def emit(session: AsyncSession, event_type: str, payload: dict[str, Any]) -> None:
    session.add(Outbox(event_type=event_type, payload=payload))
