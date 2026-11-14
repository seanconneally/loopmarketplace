"""Keep persisted local video URLs usable when the development port changes."""

from urllib.parse import urlsplit

from app.core.config import settings

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def current_media_url(value: str | None) -> str | None:
    if value is None:
        return None
    source, target = urlsplit(value), urlsplit(settings().media_public_url)
    if (
        source.hostname in LOOPBACK_HOSTS
        and target.hostname in LOOPBACK_HOSTS
        and source.path.startswith("/media/")
    ):
        return settings().media_public_url.rstrip("/") + source.path.removeprefix("/media")
    return value
