from datetime import datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Candidate(Base):
    __tablename__ = "feed_candidates"
    listing_id: Mapped[UUID] = mapped_column(primary_key=True)
    seller_id: Mapped[UUID]
    region_id: Mapped[str] = mapped_column(String(30))
    location: Mapped[Any] = mapped_column(Geography("POINT", srid=4326, spatial_index=False))
    price_cents: Mapped[int]
    make: Mapped[str] = mapped_column(String(50))
    year: Mapped[int]
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    engagement: Mapped[float] = mapped_column(default=0.0)
    public_data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (
        Index("ix_feed_location", "location", postgresql_using="gist"),
        Index("ix_feed_recency", "region_id", "published_at", "listing_id"),
        Index("ix_feed_filters", "region_id", "make", "year", "price_cents"),
    )
