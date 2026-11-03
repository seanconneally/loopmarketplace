import asyncio
import hashlib
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, require
from app.core.outbox import emit
from app.modules.listings.service import ListingService
from app.modules.media.models import MediaAsset
from app.modules.media.provider import PART_SIZE, LocalVideoProvider, VideoProvider
from app.modules.media.repository import MediaRepository
from app.modules.media.schemas import (
    MediaView,
    OwnerMediaView,
    UploadComplete,
    UploadPart,
    UploadRequest,
    UploadResume,
    UploadView,
)


def matches_generation(asset: MediaAsset, generation: int | None) -> bool:
    return asset.generation == (generation if generation is not None else 1)


class MediaService:
    def __init__(self, session: AsyncSession, provider: VideoProvider | None = None) -> None:
        self.session, self.repo = session, MediaRepository(session)
        self.provider = provider or LocalVideoProvider()

    async def _owned_asset(self, asset_id: UUID, user: UUID) -> MediaAsset:
        asset = await self.repo.get(asset_id)
        require(asset, 404, "asset_missing", "Upload not found.")
        assert asset is not None
        listing = await ListingService(self.session).owned(asset.listing_id, user, lock=True)
        require(
            listing.status not in {"sold", "removed"},
            409,
            "listing_closed",
            "Closed adverts cannot change their video.",
        )
        locked = await self.repo.get(asset_id, lock=True)
        assert locked is not None
        return locked

    async def upload(
        self, listing_id: UUID, user: UUID, data: UploadRequest, key: str
    ) -> UploadView:
        """Allocate/replay an upload, or explicitly replace failed/unfinished media on this draft."""
        listing = await ListingService(self.session).owned(listing_id, user, lock=True)
        require(
            listing.status in {"draft", "failed"},
            409,
            "invalid_state",
            "Only unfinished adverts can accept a video.",
        )
        fingerprint = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
        asset = await self.repo.by_listing(listing_id, lock=True)
        if asset and asset.idempotency_key == key:
            require(
                asset.request_hash == fingerprint,
                409,
                "idempotency_conflict",
                "This key belongs to another video.",
            )
            return await self._upload_view(asset)
        if asset:
            require(
                data.restart and asset.status in {"uploading", "failed"},
                409,
                "upload_exists",
                "Resume the saved upload or choose Start over on this advert.",
            )
            if asset.status == "uploading":
                await emit(
                    self.session,
                    "media.abort",
                    {"object_key": asset.object_key, "upload_id": asset.upload_id},
                )
            generation = asset.generation + 1
            asset_id = asset.id
        else:
            generation, asset_id = 1, uuid4()
        object_key = f"{user}/{asset_id}/v{generation}/source"
        upload_id = await asyncio.to_thread(
            self.provider.create_upload, object_key, data.content_type
        )
        if asset is None:
            asset = MediaAsset(id=asset_id, listing_id=listing_id)
            self.session.add(asset)
        asset.object_key, asset.upload_id = object_key, upload_id
        asset.size_bytes, asset.content_type = data.size, data.content_type
        asset.original_filename, asset.file_sha256 = data.name, data.file_sha256
        asset.generation, asset.status, asset.error_code = generation, "uploading", None
        asset.idempotency_key, asset.request_hash = key, fingerprint
        asset.playback_url = asset.poster_url = asset.duration = asset.perceptual_hash = None
        asset.has_audio, asset.retry_count, asset.retry_key = False, 0, None
        await self.session.flush()
        if listing.status == "failed":
            await ListingService(self.session).media_state(listing_id, "draft")
        return await self._upload_view(asset)

    async def _queue_processing(self, asset: MediaAsset) -> None:
        asset.status, asset.error_code = "processing", None
        await ListingService(self.session).media_state(asset.listing_id, "processing")
        await emit(
            self.session,
            "media.process",
            {"asset_id": str(asset.id), "generation": asset.generation},
        )

    async def _upload_view(self, asset: MediaAsset) -> UploadView:
        result = UploadView(
            asset_id=asset.id,
            upload_id=asset.upload_id,
            part_size=PART_SIZE,
            part_urls=[],
            state=asset.status,
            generation=asset.generation,
        )
        if asset.status != "uploading":
            return result
        progress = await asyncio.to_thread(
            self.provider.progress, asset.object_key, asset.upload_id, asset.size_bytes
        )
        if progress.complete:
            await self._queue_processing(asset)
            result.state = "processing"
        else:
            result.part_urls = await asyncio.to_thread(
                self.provider.part_urls, asset.object_key, asset.upload_id, asset.size_bytes
            )
            result.completed_parts = [
                UploadPart(part_number=number, etag=etag) for number, etag in progress.parts
            ]
        result.uploaded_bytes = progress.uploaded_bytes
        return result

    async def resume(self, asset_id: UUID, user: UUID, data: UploadResume) -> UploadView:
        """Refresh signed URLs and reconcile stored parts only for the identical original file."""
        asset = await self._owned_asset(asset_id, user)
        require(
            asset.file_sha256 is not None,
            409,
            "legacy_upload",
            "This older upload cannot be verified. Start over on the same advert.",
        )
        require(
            asset.file_sha256 == data.file_sha256 and asset.size_bytes == data.size,
            409,
            "file_mismatch",
            "Choose the original video to resume, or use Start over to replace it.",
        )
        return await self._upload_view(asset)

    async def complete(self, asset_id: UUID, user: UUID, data: UploadComplete) -> MediaView:
        """Finalize verified parts once; replaying completion never creates a second processing generation."""
        asset = await self._owned_asset(asset_id, user)
        require(
            asset.generation == data.generation,
            409,
            "upload_replaced",
            "This upload was replaced. Refresh the advert before continuing.",
        )
        if asset.status == "uploading":
            parts = [(part.part_number, part.etag) for part in data.parts]
            require(
                [number for number, _ in parts] == list(range(1, len(parts) + 1)),
                422,
                "invalid_parts",
                "Parts must be contiguous and ordered.",
            )
            await asyncio.to_thread(
                self.provider.complete, asset.object_key, asset.upload_id, parts, asset.size_bytes
            )
            await self._queue_processing(asset)
        return MediaView.model_validate(asset)

    async def status(self, asset_id: UUID, user: UUID) -> MediaView:
        """Expose processing status only to the draft owner."""
        asset = await self.repo.get(asset_id)
        require(asset, 404, "asset_missing", "Upload not found.")
        assert asset is not None
        await ListingService(self.session).owned(asset.listing_id, user)
        return MediaView.model_validate(asset)

    async def owner_info(self, listing_id: UUID) -> OwnerMediaView | None:
        """Supply private upload metadata to the authorized listing service."""
        asset = await self.repo.by_listing(listing_id)
        if asset is None:
            return None
        return OwnerMediaView(
            **MediaView.model_validate(asset).model_dump(),
            original_filename=asset.original_filename,
            size_bytes=asset.size_bytes,
            error_code=asset.error_code,
            retry_count=asset.retry_count,
            resumable=asset.status == "uploading" and asset.file_sha256 is not None,
        )

    async def playable(self, listing_id: UUID) -> MediaView | None:
        """Return approved playback facts to other modules."""
        asset = await self.repo.by_listing(listing_id)
        return MediaView.model_validate(asset) if asset and asset.status == "ready" else None

    async def process(self, asset_id: UUID, generation: int | None = None) -> None:
        """Encode outside row locks, then commit only if this exact generation remains current."""
        from app.modules.moderation.service import ModerationService

        asset = await self.repo.get(asset_id)
        if (
            asset is None
            or asset.status != "processing"
            or not matches_generation(asset, generation)
        ):
            return
        expected_generation, listing_id = asset.generation, asset.listing_id
        result, failure = None, None
        try:
            result = await asyncio.to_thread(
                self.provider.process,
                asset.object_key,
                f"{asset.id}/v{expected_generation}",
                asset.file_sha256,
            )
        except DomainError as exc:
            failure = exc.code
        listing = await ListingService(self.session).lock_for_media(listing_id)
        asset = await self.repo.get(asset_id, lock=True)
        if asset is None or asset.generation != expected_generation or asset.status != "processing":
            return
        if failure or listing.status in {"sold", "removed"}:
            asset.status, asset.error_code = "failed", failure or "listing_closed"
            await ListingService(self.session).media_state(listing_id, "failed")
            return
        assert result is not None
        asset.playback_url, asset.poster_url, asset.duration = (
            result.playback_url,
            result.poster_url,
            result.duration,
        )
        asset.perceptual_hash, asset.has_audio = result.perceptual_hash, result.has_audio
        review = await ModerationService(self.session).scan_listing(
            listing_id, await self.repo.duplicate(asset.id, result.perceptual_hash)
        )
        if not review:
            await asyncio.to_thread(self.provider.publish, f"{asset.id}/v{expected_generation}")
        asset.status, asset.error_code = "pending_review" if review else "ready", None
        await self.session.flush()
        await ListingService(self.session).media_state(
            listing_id, "pending_review" if review else "live"
        )

    async def approve(self, listing_id: UUID) -> None:
        """Release reviewed media without overriding a seller's pause choice."""
        asset = await self.repo.by_listing(listing_id)
        require(
            asset and asset.playback_url and asset.status == "pending_review",
            409,
            "invalid_state",
            "No processed media awaits review.",
        )
        assert asset is not None
        # Existing seed/legacy assets use an unversioned playback prefix.
        prefix = (
            f"{asset.id}/v{asset.generation}"
            if f"/{asset.id}/v" in (asset.playback_url or "")
            else str(asset.id)
        )
        await asyncio.to_thread(self.provider.publish, prefix)
        asset.status = "ready"
        await self.session.flush()
        await ListingService(self.session).media_state(listing_id, "live")

    async def require_review(self, listing_id: UUID) -> None:
        """Withdraw already processed media when edited listing text needs review."""
        asset = await self.repo.by_listing(listing_id, lock=True)
        if asset and asset.status == "ready":
            asset.status = "pending_review"
        await ListingService(self.session).media_state(listing_id, "pending_review")

    async def fail(self, asset_id: UUID, generation: int | None = None) -> None:
        """A stale exhausted job must never fail a replacement or a later retry."""
        initial = await self.repo.get(asset_id)
        if initial is None:
            return
        await ListingService(self.session).lock_for_media(initial.listing_id)
        asset = await self.repo.get(asset_id, lock=True)
        if asset and asset.status == "processing" and matches_generation(asset, generation):
            asset.status, asset.error_code = "failed", "processing_failed"
            await ListingService(self.session).media_state(asset.listing_id, "failed")

    async def _reset_failed(self, asset: MediaAsset) -> int:
        require(asset.status == "failed", 409, "invalid_state", "Only failed media can be retried.")
        asset.generation += 1
        asset.retry_count += 1
        asset.status, asset.error_code = "processing", None
        await ListingService(self.session).media_state(asset.listing_id, "processing")
        return asset.generation

    async def retry(self, asset_id: UUID, user: UUID, key: str) -> MediaView:
        """Retry the retained source once per request key, with a bounded seller retry budget."""
        asset = await self._owned_asset(asset_id, user)
        if asset.retry_key == key:
            return MediaView.model_validate(asset)
        require(
            asset.status == "failed", 409, "invalid_state", "Only failed processing can be retried."
        )
        require(
            asset.retry_count < 3,
            409,
            "retry_limit",
            "Choose a new video after three processing retries.",
        )
        require(
            await asyncio.to_thread(self.provider.source_ready, asset.object_key, asset.size_bytes),
            410,
            "source_missing",
            "The original is no longer available. Choose your video again on this advert.",
        )
        generation = await self._reset_failed(asset)
        asset.retry_key = key
        await emit(
            self.session, "media.process", {"asset_id": str(asset.id), "generation": generation}
        )
        return MediaView.model_validate(asset)

    async def retry_failed(self, asset_id: UUID) -> int:
        """Reset failed media for an explicit operator replay and return its new generation."""
        initial = await self.repo.get(asset_id)
        require(initial, 404, "asset_missing", "Upload not found.")
        assert initial is not None
        await ListingService(self.session).lock_for_media(initial.listing_id)
        asset = await self.repo.get(asset_id, lock=True)
        assert asset is not None
        return await self._reset_failed(asset)
