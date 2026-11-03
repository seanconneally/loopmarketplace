from uuid import UUID

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, IdempotencyKey, Session
from app.modules.media.schemas import (
    MediaView,
    UploadComplete,
    UploadRequest,
    UploadResume,
    UploadView,
)
from app.modules.media.service import MediaService

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/listings/{listing_id}/upload", response_model=UploadView, status_code=201)
async def upload(
    listing_id: UUID, data: UploadRequest, session: Session, user: CurrentUser, key: IdempotencyKey
) -> UploadView:
    return await MediaService(session).upload(listing_id, user, data, key)


@router.post("/{asset_id}/complete", response_model=MediaView)
async def complete(
    asset_id: UUID, data: UploadComplete, session: Session, user: CurrentUser
) -> MediaView:
    return await MediaService(session).complete(asset_id, user, data)


@router.get("/{asset_id}", response_model=MediaView)
async def status(asset_id: UUID, session: Session, user: CurrentUser) -> MediaView:
    return await MediaService(session).status(asset_id, user)


@router.post("/{asset_id}/resume", response_model=UploadView)
async def resume(
    asset_id: UUID, data: UploadResume, session: Session, user: CurrentUser
) -> UploadView:
    return await MediaService(session).resume(asset_id, user, data)


@router.post("/{asset_id}/retry", response_model=MediaView)
async def retry(
    asset_id: UUID, session: Session, user: CurrentUser, key: IdempotencyKey
) -> MediaView:
    return await MediaService(session).retry(asset_id, user, key)
