from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity


class Event(Identity, Base):
    __tablename__ = "events"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    event_type: Mapped[str] = mapped_column(String(20))
    value: Mapped[float]
    client_event_id: Mapped[UUID]
    __table_args__ = (
        UniqueConstraint("user_id", "client_event_id"),
        CheckConstraint("value >= 0 and value <= 3600", name="event_value"),
        Index("ix_events_time", "created_at", postgresql_using="brin"),
        Index("ix_events_listing", "listing_id", "event_type", "created_at"),
        Index("ix_events_user_history", "user_id", "created_at", "id"),
    )
