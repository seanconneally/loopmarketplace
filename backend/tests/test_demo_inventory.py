from collections import Counter
from unittest.mock import AsyncMock

import pytest

from app.demo_inventory import catalogue, expand


def test_pilot_fixtures_are_varied_valid_and_explicitly_synthetic():
    rows = catalogue()
    assert len(rows) == 24
    assert Counter(row.category for row in rows) == {"cars": 6, "homes": 6, "golf": 6, "other": 6}
    assert len({row.title for row in rows}) == 24
    assert len({row.area for row in rows}) == 8
    assert len({row.car.make for row in rows if row.car}) == 6
    assert all(
        row.title.startswith("Demo · ")
        and "not an item or property offered for sale" in row.description
        for row in rows
    )
    assert len({row.price_cents for row in rows}) >= 20


async def test_demo_population_refuses_non_development_environments(monkeypatch):
    from types import SimpleNamespace

    seed = AsyncMock()
    monkeypatch.setattr(
        "app.demo_inventory.settings", lambda: SimpleNamespace(app_env="test", seed_enabled=True)
    )
    monkeypatch.setattr("app.demo_inventory.seed", seed)
    with pytest.raises(RuntimeError, match="only in development"):
        await expand()
    seed.assert_not_awaited()
