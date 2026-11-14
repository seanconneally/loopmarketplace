"""Regression checks for untrusted requests, credentials and video inputs."""

import shutil
import subprocess
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.core.media_urls import current_media_url
from app.main import app
from app.modules.auth.schemas import OtpVerify
from app.modules.auth.service import AuthService
from app.modules.media.provider import VIDEO_INPUT_OPTIONS


def test_short_signing_keys_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret="short")


@pytest.mark.parametrize(
    "origin",
    ["javascript:alert(1)", "https://host.example/reset", "https://user:pass@host.example"],
)
def test_public_origin_cannot_contain_credentials_or_a_reset_path(origin: str) -> None:
    with pytest.raises(ValidationError, match="PUBLIC_ORIGIN"):
        Settings(public_origin=origin)


@pytest.mark.parametrize("sid", [None, 123, [], {}, "not-a-uuid"])
async def test_malformed_signed_identity_is_unauthorized(sid: object) -> None:
    now = utcnow()
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "sid": sid,
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=1),
            "iss": "motorloop",
            "aud": "motorloop-web",
        },
        settings().jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(DomainError) as error:
        await AuthService(AsyncMock()).authenticate(token)
    assert error.value.status == 401
    assert error.value.code == "invalid_token"


def test_otp_uses_ascii_digits() -> None:
    with pytest.raises(ValidationError):
        OtpVerify(phone="+353871234567", code="١٢٣٤٥٦")


def test_saved_local_media_follows_the_configured_preview_port(monkeypatch):
    monkeypatch.setattr(
        "app.core.media_urls.settings",
        lambda: SimpleNamespace(media_public_url="http://localhost:8088/media"),
    )
    path = f"/media/{uuid4()}/v1/master.m3u8"
    assert current_media_url(f"http://localhost:8080{path}") == f"http://localhost:8088{path}"
    assert current_media_url(None) is None
    assert current_media_url(f"https://cdn.example{path}") == f"https://cdn.example{path}"


async def test_throttled_api_responses_still_have_security_headers(monkeypatch):
    monkeypatch.setattr("app.main.rate_limit", AsyncMock(return_value=False))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=settings().public_origin
    ) as client:
        response = await client.post("/api/v1/auth/otp/request", json={"phone": "+353871234567"})
    assert response.status_code == 429
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["retry-after"] == "60"
    assert response.headers["x-request-id"] == response.json()["error"]["request_id"]


@pytest.mark.parametrize("origin", [None, "https://attacker.example", "null"])
async def test_cross_origin_sms_requests_never_create_a_challenge(monkeypatch, origin):
    monkeypatch.setattr("app.main.rate_limit", AsyncMock(return_value=True))
    challenge = AsyncMock()
    monkeypatch.setattr(AuthService, "challenge", challenge)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=settings().public_origin
    ) as client:
        response = await client.post(
            "/api/v1/auth/otp/request",
            headers={"Origin": origin} if origin else {},
            json={"phone": "+353871234567"},
        )
    assert response.status_code == 403
    challenge.assert_not_awaited()


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe is in the app image")
def test_disguised_playlist_cannot_be_decoded_as_uploaded_video(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_text("#EXTM3U\n#EXTINF:15,\nhttp://127.0.0.1:1/private\n#EXT-X-ENDLIST\n")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", *VIDEO_INPUT_OPTIONS, str(source)],
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert probe.returncode != 0
    # It must fail at the demuxer boundary, before resolving playlist resources.
    assert b"not on whitelist" in probe.stderr or b"Invalid data" in probe.stderr
