import asyncio
import os
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.db import sessions, utcnow
from app.modules.analytics.schemas import EventInput
from app.modules.feed.ranking import HeuristicRanker, build_profile, recommend
from app.modules.feed.schemas import FeedFilters
from app.modules.feed.service import FeedService
from app.modules.listings.schemas import ListingCreate, ListingUpdate, ListingView
from app.modules.listings.service import ListingService
from app.modules.users.models import User
from tests.test_personal_feed import item, signal
from tests.test_seller_uploads import BODY


def test_category_validation_and_cross_category_prices():
    home = ListingCreate.model_validate(
        {
            **BODY,
            "category": "homes",
            "car": None,
            "price_cents": 48500000,
            "attributes": {"bedrooms": 3},
        }
    )
    assert home.car is None and home.attributes["bedrooms"] == 3
    for patch in [
        {"category": "homes"},
        {"category": "cars", "car": None},
        {"category": "golf", "car": None, "attributes": {"bedrooms": 3}},
        {"category": "homes", "car": None, "attributes": {"bedrooms": -1}},
    ]:
        with pytest.raises(ValidationError):
            ListingCreate.model_validate({**BODY, **patch})
    car, golf, home_item = item(), item(), item()
    golf.public_data = {"category": "golf", "attributes": {"brand": "Sample", "club_type": "irons"}}
    golf.price_cents = 32000
    home_item.public_data = {"category": "homes", "attributes": {"bedrooms": 3}}
    home_item.price_cents = 48500000
    facts = {row.listing_id: row for row in [car, golf, home_item]}
    profile = build_profile([signal(golf, "save")], facts, utcnow())
    assert set(profile.prices) == {"golf"}
    assert profile.score(home_item) == 0
    assert profile.score(golf) > profile.score(car)
    repeated = build_profile([signal(golf, "replay", 2)] * 100, facts, utcnow())
    assert repeated.affinities["category:golf"] < 6
    ordered = recommend([car, golf, home_item], utcnow(), set(), profile, HeuristicRanker())
    assert ordered[0] == golf


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires Compose dependencies")
async def test_generic_inventory_edit_search_filter_and_projection():
    async with sessions() as session:
        owner = User(
            phone=f"+3538{uuid4().int % 10**8:08}", verified_at=utcnow(), adult_declared=True
        )
        session.add(owner)
        await session.flush()
        marker = f"Mixed-{uuid4().hex[:8]}"
        service, feed = ListingService(session), FeedService(session)
        rows = []
        for category, price, attrs in [
            ("cars", 2000000, {}),
            ("homes", 48500000, {"bedrooms": 3}),
            ("golf", 32000, {"brand": "Mizuno", "club_type": "irons"}),
            ("other", 8500, {"condition": "good"}),
        ]:
            data = ListingCreate.model_validate(
                {
                    **BODY,
                    "title": f"{marker} {category}",
                    "category": category,
                    "car": BODY["car"] if category == "cars" else None,
                    "price_cents": price,
                    "attributes": attrs,
                }
            )
            row = await service.create(owner.id, data, str(uuid4()))
            row.status, row.published_at = "live", utcnow()
            await session.flush()
            await feed.project(await service.detail(row.id), row.latitude, row.longitude)
            rows.append(row)
        mixed = await feed.page(FeedFilters(q=marker), None, None)
        assert {row.category for row in mixed.items} == {"cars", "homes", "golf", "other"}
        golf = await feed.page(FeedFilters(q=marker, category="golf"), None, None)
        assert len(golf.items) == 1 and golf.items[0].car is None
        assert (await feed.page(FeedFilters(q=f"{marker} Mizuno"), None, None)).items[
            0
        ].category == "golf"
        cars = await feed.page(FeedFilters(q=marker, fuel="petrol"), None, None)
        assert all(row.category == "cars" for row in cars.items)
        home = rows[1]
        original = await service.detail(home.id, owner.id)
        update = ListingUpdate.model_validate(
            {
                **original.model_dump(),
                "latitude": home.latitude,
                "longitude": home.longitude,
                "revision": home.revision,
                "rights_confirmed": True,
                "attributes": {"property_type": "apartment", "bedrooms": 2},
            }
        )
        edited = await service.update(home.id, owner.id, update)
        assert edited.attributes["bedrooms"] == 2 and edited.car is None
        await session.rollback()


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires Compose dependencies")
async def test_adaptive_windows_and_concurrent_retries(monkeypatch):
    """Use the real Redis CAS with isolated in-memory inventory, no shared DB transaction."""
    from app.modules.feed.repository import FeedRepository
    from app.modules.users.service import UserService

    user = uuid4()
    rows = [item("Toyota" if i < 8 else "BMW") for i in range(16)]
    views = {
        row.listing_id: ListingView.model_validate(
            {
                **BODY,
                "id": row.listing_id,
                "status": "live",
                "currency": "EUR",
                "region_id": "ie-dublin",
                "category": "cars",
                "published_at": row.published_at,
                "seller": {"id": row.seller_id, "name": "Seller", "dealer_verified": False},
            }
        )
        for row in rows
    }
    preference = ["Toyota"]

    async def active(*_):
        return SimpleNamespace(analytics_consent=True)

    async def cutoff(*_):
        return None

    async def candidates(*_, **__):
        return rows

    async def by_ids(_, ids):
        return [row for row in rows if row.listing_id in ids]

    async def profile(*_):
        matching = [row for row in rows if row.make == preference[0]]
        return build_profile(
            [signal(row, "save") for row in matching],
            {row.listing_id: row for row in rows},
            utcnow(),
        )

    async def visible(_, ids, *__):
        await asyncio.sleep(0.01)
        return [views[value] for value in ids]

    monkeypatch.setattr(UserService, "active", active)
    monkeypatch.setattr(FeedRepository, "cutoff", cutoff)
    monkeypatch.setattr(FeedRepository, "candidates", candidates)
    monkeypatch.setattr(FeedRepository, "by_ids", by_ids)
    monkeypatch.setattr(FeedService, "interest_profile", profile)
    monkeypatch.setattr(FeedService, "_visible", visible)
    feed = FeedService(None)
    filters = FeedFilters(q=f"cas-{uuid4().hex}")
    first = await feed.page(filters, user, None)
    assert len(first.items) == 4 and first.next_cursor
    assert next(row for row in rows if row.listing_id == first.items[0].id).make == "Toyota"
    assert (
        sum(
            next(row for row in rows if row.listing_id == value.id).make == "Toyota"
            for value in first.items
        )
        >= 2
    )
    preference[0] = "BMW"
    second, simultaneous = await asyncio.gather(
        feed.page(filters, user, first.next_cursor), feed.page(filters, user, first.next_cursor)
    )
    assert [row.id for row in second.items] == [row.id for row in simultaneous.items]
    assert second.next_cursor == simultaneous.next_cursor
    assert not {row.id for row in first.items} & {row.id for row in second.items}
    assert next(row for row in rows if row.listing_id == second.items[0].id).make == "BMW"
    preference[0] = "Toyota"
    retry = await feed.page(filters, user, first.next_cursor)
    assert [row.id for row in retry.items] == [row.id for row in second.items]


def test_old_or_unbounded_playback_receipts_are_rejected():
    for patch in [{"occurred_at": utcnow() - timedelta(minutes=2)}, {"value": 3}]:
        with pytest.raises(ValidationError):
            EventInput(client_event_id=uuid4(), listing_id=uuid4(), event_type="replay", **patch)
