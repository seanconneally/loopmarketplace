from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    size: int = Field(gt=0, le=500 * 1024 * 1024)
    content_type: Literal["video/mp4", "video/quicktime"]
    file_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    restart: bool = False


class UploadResume(BaseModel):
    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size: int = Field(gt=0, le=500 * 1024 * 1024)


class UploadView(BaseModel):
    asset_id: UUID
    upload_id: str
    part_size: int
    part_urls: list[str]
    completed_parts: list["UploadPart"] = Field(default_factory=list)
    uploaded_bytes: int = 0
    state: str = "uploading"
    generation: int = 1


class UploadPart(BaseModel):
    part_number: int = Field(ge=1, le=64)
    etag: str = Field(min_length=1, max_length=100)


class UploadComplete(BaseModel):
    parts: list[UploadPart] = Field(min_length=1, max_length=64)
    generation: int = Field(default=1, ge=1)


class MediaView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    listing_id: UUID
    status: str
    playback_url: str | None
    poster_url: str | None
    duration: float | None
    has_audio: bool = False


class OwnerMediaView(MediaView):
    original_filename: str
    size_bytes: int
    error_code: str | None
    retry_count: int
    resumable: bool
