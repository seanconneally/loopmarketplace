import base64
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.errors import DomainError


def encode_cursor(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(settings().jwt_secret.encode(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature + raw).decode().rstrip("=")


def decode_cursor(value: str) -> dict[str, Any]:
    try:
        payload = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        signature, raw = payload[:32], payload[32:]
        expected = hmac.new(settings().jwt_secret.encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        result: dict[str, Any] = json.loads(raw)
        return result
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise DomainError(
            400, "invalid_cursor", "Restart this list; its cursor is invalid."
        ) from exc


def cursor_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise DomainError(400, "invalid_cursor", "Cursor time is invalid.") from exc
