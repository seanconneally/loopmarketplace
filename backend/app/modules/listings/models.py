from datetime import datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity


class Listing(Identity, Base):
    __tablename__ = "listings"
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(30), default="cars")
    region_id: Mapped[str] = mapped_column(String(30), default="ie-dublin")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(3000), default="")
    price_cents: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    latitude: Mapped[float]
    longitude: Mapped[float]
    location: Mapped[Any] = mapped_column(
        Geography("POINT", srid=4326, spatial_index=False),
        Computed("ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography", persisted=True),
    )
    area: Mapped[str] = mapped_column(String(100))
    rights_confirmed: Mapped[bool] = mapped_column(default=False)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(default=1, server_default="1")
    is_paused: Mapped[bool] = mapped_column(default=False, server_default="false")
    __table_args__ = (
        UniqueConstraint("seller_id", "idempotency_key"),
        CheckConstraint("price_cents > 0", name="positive_price"),
        CheckConstraint(
            "latitude between -90 and 90 and longitude between -180 and 180", name="coordinates"
        ),
        CheckConstraint(
            "status in ('draft','processing','pending_review','live','paused','sold','removed','failed')",
            name="valid_status",
        ),
        Index("ix_listings_live_recency", "published_at", "id", postgresql_where=status == "live"),
        Index("ix_listings_location", "location", postgresql_using="gist"),
        Index("ix_listings_owner_history", "seller_id", "created_at", "id"),
    )


class CarDetails(Base):
    __tablename__ = "car_details"
    listing_id: Mapped[UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True
    )
    make: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(60))
    year: Mapped[int]
    mileage_km: Mapped[int]
    fuel: Mapped[str] = mapped_column(String(20))
    transmission: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        CheckConstraint("year between 1900 and 2100", name="year_range"),
        CheckConstraint("mileage_km >= 0", name="nonnegative_mileage"),
    )


class Save(Base):
    __tablename__ = "saves"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    listing_id: Mapped[UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True
    )
    __table_args__ = (Index("ix_saves_listing", "listing_id"),)
