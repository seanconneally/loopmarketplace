import os
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.db import sessions, utcnow
from app.core.errors import DomainError
from app.modules.analytics.models import Event
from app.modules.analytics.schemas import InterestEvent
from app.modules.analytics.service import AnalyticsService
from app.modules.feed.ranking import HeuristicRanker, InterestProfile, build_profile, recommend
from app.modules.feed.schemas import FeedFilters
from app.modules.feed.service import FeedService
from app.modules.listings.schemas import ListingCreate
from app.modules.listings.service import ListingService
from app.modules.media.models import MediaAsset
from app.modules.users.models import User
from app.modules.users.schemas import ProfileUpdate
from app.modules.users.service import UserService
from tests.test_seller_uploads import BODY


def item(make="Toyota", seller=None, age=0):
    return SimpleNamespace(
        listing_id=uuid4(),
        seller_id=seller or uuid4(),
        make=make,
        price_cents=2000000,
        published_at=utcnow() - timedelta(hours=age),
        engagement=0,
        public_data={
            "car": {"fuel": "hybrid" if make == "Toyota" else "diesel", "transmission": "automatic"}
        },
    )


def signal(row, kind="completion", value=1, age=0):
    return InterestEvent(
        listing_id=row.listing_id,
        event_type=kind,
        value=value,
        created_at=utcnow() - timedelta(days=age),
    )


def test_completion_and_real_intent_learn_different_interests_and_skips():
    toyota, bmw = item(), item("BMW")
    facts = {row.listing_id: row for row in [toyota, bmw]}
    profile = build_profile([signal(toyota), signal(bmw, value=0.02)], facts, utcnow())
    assert profile.score(toyota) > profile.score(bmw)
    assert profile.affinities["cars:make:bmw"] < 0
    assert recommend([bmw, toyota], utcnow(), set(), profile, HeuristicRanker())[0] == toyota
    opposite = build_profile([signal(bmw, "message")], facts, utcnow())
    assert opposite.score(bmw) > opposite.score(toyota)


def test_repeated_receipts_are_capped_and_old_interests_decay():
    row = item()
    facts = {row.listing_id: row}
    once = build_profile([signal(row, "save")], facts, utcnow())
    many = build_profile([signal(row, "save") for _ in range(100)], facts, utcnow())
    assert many.affinities["cars:make:toyota"] == pytest.approx(
        once.affinities["cars:make:toyota"], rel=0.001
    )
    old = build_profile([signal(row, "save", age=14)], facts, utcnow())
    assert old.affinities["cars:make:toyota"] == pytest.approx(1, rel=0.001)


def test_diversity_exploration_and_small_inventories_never_drop_or_duplicate_items():
    seller = uuid4()
    rows = [item(seller=seller, age=24) for _ in range(7)] + [
        item("BMW"),
        item("Honda"),
        item("Volvo"),
    ]
    profile = InterestProfile({"cars:make:toyota": 30})
    result = recommend(rows, utcnow(), set(), profile, HeuristicRanker())
    assert len(result) == len(rows)
    assert len({row.listing_id for row in result}) == len(rows)
    assert any(row.make != "Toyota" for row in result[:5])
    assert recommend(rows[:1], utcnow(), set(), profile, HeuristicRanker()) == rows[:1]
    assert recommend([], utcnow(), set(), profile, HeuristicRanker()) == []


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires Compose dependencies")
async def test_personal_feed_filters_feedback_reset_consent_and_real_actions():
    async with sessions() as session:
        owner, alice, bob = [
            User(
                phone=f"+3538{uuid4().int % 10**8:08}",
                verified_at=utcnow(),
                adult_declared=True,
                analytics_consent=True,
            )
            for _ in range(3)
        ]
        session.add_all([owner, alice, bob])
        await session.flush()
        marker = f"Interest-{uuid4().hex[:8]}"
        listings = []
        published = utcnow() - timedelta(hours=1)
        for index in range(15):
            data = ListingCreate.model_validate(
                {
                    **BODY,
                    "title": f"{marker} {index}",
                    "price_cents": 2000000 + index * 1000,
                    "car": {
                        **BODY["car"],
                        "make": "Toyota" if index % 2 == 0 else "BMW",
                        "fuel": "hybrid" if index % 2 == 0 else "diesel",
                    },
                }
            )
            row = await ListingService(session).create(owner.id, data, str(uuid4()))
            row.published_at = published
            session.add(
                MediaAsset(
                    listing_id=row.id,
                    object_key=f"interest-fixture/{uuid4()}",
                    upload_id="fixture",
                    size_bytes=1,
                    content_type="video/mp4",
                    idempotency_key=str(uuid4()),
                    request_hash="0" * 64,
                    status="ready",
                    playback_url="http://localhost:8080/media/test/master.m3u8",
                )
            )
            await session.flush()
            await ListingService(session).media_state(row.id, "live")
            listings.append(row)
        service = FeedService(session)
        filters = FeedFilters(q=marker)
        await ListingService(session).save(listings[0].id, alice.id, True)
        await ListingService(session).save(listings[0].id, alice.id, True)
        await ListingService(session).save(listings[1].id, bob.id, True)
        await session.flush()
        assert (
            await session.scalar(
                select(func.count()).select_from(Event).where(Event.user_id == alice.id)
            )
            == 1
        )
        first = await service.page(filters, alice.id, None)
        other = await service.page(filters, bob.id, None)
        assert first.ranking == "interest-v2"
        assert first.items[0].car.make == "Toyota"
        assert other.items[0].car.make == "BMW"
        assert first.next_cursor
        await service.dismiss(alice.id, listings[0].id)
        hidden = await service.page(filters, alice.id, None)
        assert listings[0].id not in {row.id for row in hidden.items}
        assert listings[0].id in {
            row.id
            for row in (
                await service.page(FeedFilters(q=marker, make="Toyota"), bob.id, None)
            ).items
        }
        await service.undo_dismiss(alice.id, listings[0].id)
        assert not await session.scalar(
            select(Event.id).where(Event.user_id == alice.id, Event.event_type == "not_interested")
        )
        constrained = await service.page(
            FeedFilters(q=marker, make="BMW", max_price=2010000, sort="price_asc"), alice.id, None
        )
        assert all(
            row.car.make == "BMW" and row.price_cents <= 2010000 for row in constrained.items
        )
        assert [row.price_cents for row in constrained.items] == sorted(
            row.price_cents for row in constrained.items
        )
        await service.reset_preferences(alice.id)
        with pytest.raises(DomainError) as changed:
            await service.page(filters, alice.id, first.next_cursor)
        assert changed.value.status == 410
        assert (
            await service.interest_profile(alice.id, await service.repo.cutoff(alice.id))
        ).signals == 0
        await UserService(session).update(
            alice.id, ProfileUpdate(name="Alice", adult_declared=True, analytics_consent=False)
        )
        await ListingService(session).save(listings[2].id, alice.id, True)
        await session.flush()
        assert (
            await session.scalar(
                select(func.count()).select_from(Event).where(Event.user_id == alice.id)
            )
            == 1
        )
        assert await AnalyticsService(session).recent(alice.id, utcnow() - timedelta(days=30)) == []
        assert not await service.accepts_signal_time(alice.id, published)
        await session.rollback()
