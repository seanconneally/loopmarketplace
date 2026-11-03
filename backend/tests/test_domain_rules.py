from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.db import utcnow
from app.core.errors import DomainError
from app.core.paging import decode_cursor, encode_cursor
from app.modules.feed.ranking import HeuristicRanker
from app.modules.listings.schemas import ListingCreate
from app.modules.moderation.service import scam_warnings
from app.modules.viewings.schemas import ViewingInput
from app.modules.viewings.service import ics_escape


def test_cursor_rejects_tampering() -> None:
    cursor = encode_cursor({"id": str(uuid4()), "filters": "abc"})
    assert decode_cursor(cursor)["filters"] == "abc"
    with pytest.raises(DomainError):
        decode_cursor(("A" if cursor[0] != "A" else "B") + cursor[1:])


def test_seen_penalty_exceeds_maximum_engagement_boost() -> None:
    @dataclass
    class Candidate:
        listing_id: UUID
        published_at: object
        engagement: float

    from types import SimpleNamespace

    now = utcnow()
    fresh = SimpleNamespace(listing_id=uuid4(), published_at=now, engagement=0.0)
    seen = SimpleNamespace(listing_id=uuid4(), published_at=now, engagement=10**20)
    ranker = HeuristicRanker()
    assert ranker.score(fresh, now, False) > ranker.score(seen, now, True)
    older = SimpleNamespace(listing_id=uuid4(), published_at=now - timedelta(days=2), engagement=0)
    assert ranker.score(fresh, now, False) > ranker.score(older, now, False)


def test_production_refuses_development_adapters() -> None:
    with pytest.raises(ValidationError, match="Production adapters"):
        Settings(app_env="production")


def test_scam_signals_warn_without_claiming_certainty() -> None:
    assert (
        len(scam_warnings("Pay the deposit to https://pay.example and my courier will collect"))
        == 3
    )
    assert scam_warnings("Can we view the car tomorrow at the shopping centre?") == []


def test_calendar_fields_cannot_inject_an_event() -> None:
    assert ics_escape("Street, A;B\r\nEND:VEVENT") == "Street\\, A\\;B\\nEND:VEVENT"


def test_viewing_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        ViewingInput(
            conversation_id=uuid4(), starts_at="2027-01-01T12:00:00", place="Public meeting place"
        )  # type: ignore[arg-type]


def test_listing_rejects_unowned_content_and_out_of_region_location() -> None:
    with pytest.raises(ValidationError):
        ListingCreate.model_validate({"rights_confirmed": False, "latitude": 0, "longitude": 0})


def test_search_canonicalizes_text_and_rejects_reversed_ranges() -> None:
    from app.modules.feed.schemas import FeedFilters

    assert FeedFilters(q="  Toyota   YARIS ", make=" TOYOTA ").q == "toyota yaris"
    assert FeedFilters(q="   ").q is None
    for values in [
        {"min_price": 500, "max_price": 100},
        {"min_year": 2026, "max_year": 2020},
        {"q": " ".join(["word"] * 9)},
    ]:
        with pytest.raises(ValidationError):
            FeedFilters.model_validate(values)


def test_multipart_completion_recovers_a_lost_success_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from botocore.exceptions import ClientError

    from app.modules.media.provider import LocalVideoProvider

    class CompletedStorage:
        def list_parts(self, **kwargs):
            raise ClientError({"Error": {"Code": "NoSuchUpload"}}, "ListParts")

        def head_object(self, **kwargs):
            return {"ContentLength": 1000}

    monkeypatch.setattr("app.modules.media.provider.storage", lambda: CompletedStorage())
    provider = LocalVideoProvider()
    provider.complete("owned/object", "completed-upload", [(1, '"part"')], 1000)
    with pytest.raises(DomainError, match="Completed object size"):
        provider.complete("owned/object", "completed-upload", [(1, '"part"')], 2000)
