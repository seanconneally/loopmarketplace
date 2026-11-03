from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, Identity


class MediaAsset(Identity, Base):
    __tablename__ = "media_assets"
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(30), default="local-ffmpeg")
    status: Mapped[str] = mapped_column(String(20), default="uploading")
    object_key: Mapped[str] = mapped_column(String(240), unique=True)
    upload_id: Mapped[str] = mapped_column(String(300))
    size_bytes: Mapped[int]
    content_type: Mapped[str] = mapped_column(String(50))
    playback_url: Mapped[str | None] = mapped_column(String(500))
    poster_url: Mapped[str | None] = mapped_column(String(500))
    duration: Mapped[float | None]
    perceptual_hash: Mapped[str | None] = mapped_column(String(32), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str] = mapped_column(String(200), default="", server_default="")
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    generation: Mapped[int] = mapped_column(default=1, server_default="1")
    retry_count: Mapped[int] = mapped_column(default=0, server_default="0")
    retry_key: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    has_audio: Mapped[bool] = mapped_column(default=False, server_default="false")
    __table_args__ = (
        CheckConstraint("size_bytes > 0 and size_bytes <= 524288000", name="size_limit"),
    )
