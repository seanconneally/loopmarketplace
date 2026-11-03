import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.db import sessions
from app.main import app
from app.modules.feed.models import Candidate
from app.modules.listings.service import ListingService
from app.modules.media.models import MediaAsset
from app.modules.media.provider import PART_SIZE, LocalVideoProvider, storage
from app.modules.media.service import MediaService
from app.modules.moderation.models import Report
from tests.test_integration import login

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires Compose dependencies"),
]

BODY = {
    "title": "Seller lifecycle car",
    "description": "Full service history.",
    "price_cents": 1200000,
    "area": "Dublin",
    "latitude": 53.3498,
    "longitude": -6.2603,
    "rights_confirmed": True,
    "car": {
        "make": "Toyota",
        "model": "Yaris",
        "year": 2020,
        "mileage_km": 40000,
        "fuel": "hybrid",
        "transmission": "automatic",
    },
}


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=app, client=(f"198.18.{uuid4().int % 256}.{uuid4().int % 256}", 12345)
        ),
        base_url="http://localhost:8080",
        headers={"Origin": "http://localhost:8080"},
    )


async def create(owner: httpx.AsyncClient) -> str:
    response = await owner.post(
        "/api/v1/listings", json=BODY, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_owner_edit_conflicts_pause_projection_and_review() -> None:
    async with client() as owner, client() as other:
        await login(owner)
        await login(other)
        listing_id = await create(owner)
        async with sessions() as session:
            # A processed, approved media fixture; real encoding is exercised separately below.
            session.add(
                MediaAsset(
                    listing_id=UUID(listing_id),
                    object_key=f"test/{uuid4()}",
                    upload_id="fixture",
                    size_bytes=1,
                    content_type="video/mp4",
                    idempotency_key=str(uuid4()),
                    request_hash="0" * 64,
                    status="ready",
                    playback_url="http://localhost:8080/media/test/master.m3u8",
                    has_audio=True,
                )
            )
            await session.flush()
            await ListingService(session).media_state(UUID(listing_id), "live")
            await session.commit()
        path = f"/api/v1/listings/{listing_id}"
        own = (await owner.get(f"{path}/owner")).json()
        assert (await other.get(f"{path}/owner")).status_code == 403
        assert all(
            row["id"] != listing_id
            for row in (await other.get("/api/v1/listings/mine")).json()["items"]
        )
        patch = {**BODY, "price_cents": 1100000, "revision": own["revision"]}
        assert (await other.patch(path, json=patch)).status_code == 403
        edited = await owner.patch(path, json=patch)
        assert edited.status_code == 200, edited.text
        assert (await owner.patch(path, json=patch)).status_code == 409
        async with sessions() as session:
            candidate = await session.get(Candidate, UUID(listing_id))
            assert (
                candidate
                and candidate.price_cents == 1100000
                and candidate.public_data["has_audio"]
            )
        paused = await owner.post(f"{path}/pause", json={"revision": edited.json()["revision"]})
        assert paused.status_code == 200 and paused.json()["status"] == "paused", paused.text
        assert paused.json()["is_paused"]
        assert (await other.get(path)).status_code == 404
        async with sessions() as session:
            assert await session.get(Candidate, UUID(listing_id)) is None
        resumed = await owner.post(f"{path}/resume", json={"revision": paused.json()["revision"]})
        assert resumed.status_code == 200 and resumed.json()["status"] == "live", resumed.text
        paused_again = await owner.post(
            f"{path}/pause", json={"revision": resumed.json()["revision"]}
        )
        assert paused_again.status_code == 200
        # Flagged edits withdraw the advert, and cannot be published through the seller action.
        flagged = await owner.patch(
            path,
            json={
                **patch,
                "description": "Visit https://external.example",
                "revision": paused_again.json()["revision"],
            },
        )
        assert flagged.status_code == 200 and flagged.json()["status"] == "pending_review", (
            flagged.text
        )
        assert (
            await owner.post(f"{path}/resume", json={"revision": flagged.json()["revision"]})
        ).status_code == 409
        # A new edit with the same flagged text still gets its own review, even after an earlier review was resolved.
        async with sessions() as session:
            for report in await session.scalars(
                select(Report).where(Report.target_id == UUID(listing_id))
            ):
                report.status = "resolved"
            await session.commit()
        again = await owner.patch(
            path,
            json={
                **patch,
                "description": "Visit https://external.example",
                "revision": flagged.json()["revision"],
            },
        )
        assert again.status_code == 200, again.text
        async with sessions() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(Report)
                    .where(Report.target_id == UUID(listing_id), Report.status == "open")
                )
                == 1
            )
            assert await session.get(Candidate, UUID(listing_id)) is None
            await MediaService(session).approve(UUID(listing_id))
            await session.commit()
        approved = (await owner.get(f"{path}/owner")).json()
        assert approved["status"] == "paused" and approved["is_paused"]
        sold = await owner.post(f"{path}/sold")
        assert sold.status_code == 200 and sold.json()["status"] == "sold", sold.text
        assert (
            await owner.patch(path, json={**patch, "revision": approved["revision"]})
        ).status_code == 409


async def test_real_multipart_resume_file_identity_replacement_and_retry() -> None:
    async with client() as owner, client() as other:
        await login(owner)
        await login(other)
        listing_id = await create(owner)
        body = b"x" * (PART_SIZE + 27)
        digest = hashlib.sha256(body).hexdigest()
        allocation = await owner.post(
            f"/api/v1/media/listings/{listing_id}/upload",
            json={
                "name": "original.mp4",
                "size": len(body),
                "content_type": "video/mp4",
                "file_sha256": digest,
            },
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert allocation.status_code == 201, allocation.text
        upload = allocation.json()
        asset_id = upload["asset_id"]
        async with httpx.AsyncClient() as direct:
            first = await direct.put(upload["part_urls"][0], content=body[:PART_SIZE])
            assert first.status_code == 200, first.text
        path = f"/api/v1/media/{asset_id}"
        resume = {"file_sha256": digest, "size": len(body)}
        assert (await other.post(f"{path}/resume", json=resume)).status_code == 403
        assert (
            await owner.post(f"{path}/resume", json={**resume, "file_sha256": "0" * 64})
        ).status_code == 409
        recovered = await owner.post(f"{path}/resume", json=resume)
        assert recovered.status_code == 200, recovered.text
        assert recovered.json()["uploaded_bytes"] == PART_SIZE
        assert recovered.json()["completed_parts"] == [
            {"part_number": 1, "etag": first.headers["etag"]}
        ]
        replacement = await owner.post(
            f"/api/v1/media/listings/{listing_id}/upload",
            json={
                "name": "replacement.mp4",
                "size": 27,
                "content_type": "video/mp4",
                "file_sha256": hashlib.sha256(b"y" * 27).hexdigest(),
                "restart": True,
            },
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert replacement.status_code == 201, replacement.text
        assert replacement.json()["asset_id"] == asset_id and replacement.json()["generation"] == 2
        assert (
            await owner.post(
                f"{path}/complete",
                json={
                    "generation": 1,
                    "parts": [{"part_number": 1, "etag": first.headers["etag"]}],
                },
            )
        ).status_code == 409
        async with sessions() as session:
            media = await session.get(MediaAsset, UUID(asset_id))
            assert media
            storage().put_object(
                Bucket=settings().source_bucket, Key=media.object_key, Body=b"y" * 27
            )
            media.status = "failed"
            media.error_code = "processing_failed"
            await ListingService(session).media_state(UUID(listing_id), "failed")
            await session.commit()
        key = {"Idempotency-Key": str(uuid4())}
        retried = await owner.post(f"{path}/retry", headers=key)
        assert retried.status_code == 200, retried.text
        assert (await owner.post(f"{path}/retry", headers=key)).status_code == 200
        async with sessions() as session:
            media = await session.get(MediaAsset, UUID(asset_id))
            assert media
            assert media.generation == 3 and media.retry_count == 1
            await MediaService(session).fail(media.id, 1)
            assert media.generation == 3
            await ListingService(session).media_state(UUID(listing_id), "removed")
            await session.commit()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="Run inside the app image for ffmpeg")
@pytest.mark.parametrize("silent", [False, True])
def test_actual_hls_keeps_audio_and_accepts_silent_input(silent: bool) -> None:
    cfg, s3 = settings(), storage()
    prefix = f"test-audio/{uuid4()}"
    try:
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / "clip.mp4"
            subprocess.run(
                [
                    "python",
                    "scripts/make_test_video.py",
                    str(source),
                    *(["--silent"] if silent else []),
                ],
                check=True,
            )
            s3.upload_file(str(source), cfg.source_bucket, f"{prefix}/source")
            result = LocalVideoProvider().process(f"{prefix}/source", prefix)
            assert result.has_audio is not silent
            for height in (640, 1280):
                segment = Path(temporary) / f"{height}.ts"
                s3.download_file(
                    cfg.source_bucket, f"processed/{prefix}/{height}/0000.ts", str(segment)
                )
                probe = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        "a",
                        "-show_entries",
                        "stream=codec_name",
                        "-of",
                        "csv=p=0",
                        str(segment),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                assert ("aac" in probe.stdout) is not silent
    finally:
        for object_prefix in (prefix, f"processed/{prefix}"):
            for page in s3.get_paginator("list_objects_v2").paginate(
                Bucket=cfg.source_bucket, Prefix=object_prefix
            ):
                for item in page.get("Contents", []):
                    s3.delete_object(Bucket=cfg.source_bucket, Key=item["Key"])
