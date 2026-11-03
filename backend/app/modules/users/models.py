from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity


class User(Identity, Base):
    __tablename__ = "users"
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(80), default="Motorloop member")
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    role: Mapped[str] = mapped_column(String(12), default="member")
    status: Mapped[str] = mapped_column(String(12), default="active")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adult_declared: Mapped[bool] = mapped_column(default=False)
    analytics_consent: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (
        CheckConstraint("role in ('member','dealer','admin')", name="valid_role"),
        CheckConstraint("status in ('active','suspended','deleted')", name="valid_status"),
    )


class Dealer(Identity, Base):
    __tablename__ = "dealers"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    business_name: Mapped[str] = mapped_column(String(120))
    registration_number: Mapped[str] = mapped_column(String(80))
    address: Mapped[str] = mapped_column(String(240))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
