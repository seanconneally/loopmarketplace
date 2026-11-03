import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.modules.analytics.schemas import InterestEvent


class Rankable(Protocol):
    listing_id: UUID
    published_at: datetime
    engagement: float


class FeedRanker(Protocol):
    def score(self, item: Rankable, now: datetime, seen: bool) -> float: ...


class HeuristicRanker:
    def score(self, item: Rankable, now: datetime, seen: bool) -> float:
        age_hours = max(0.0, (now - item.published_at).total_seconds() / 3600)
        return (
            -math.log1p(age_hours)
            + min(1.0, math.log1p(max(0, item.engagement)) / 10)
            - (1.5 if seen else 0)
        )


class RecommendationItem(Rankable, Protocol):
    seller_id: UUID
    make: str | None
    price_cents: int
    public_data: dict[str, Any]


def category(item: RecommendationItem) -> str:
    return str(item.public_data.get("category", "cars"))


def features(item: RecommendationItem) -> dict[str, float]:
    kind = category(item)
    car = item.public_data.get("car") or {}
    attrs = item.public_data.get("attributes") or {}
    values = {f"category:{kind}": 2.0}
    if kind == "cars":
        values.update(
            {
                f"cars:make:{(item.make or '').lower()}": 1.8,
                f"cars:fuel:{car.get('fuel', '')}": 0.8,
                f"cars:transmission:{car.get('transmission', '')}": 0.4,
            }
        )
    for key in ("brand", "club_type", "hand", "property_type", "condition"):
        if attrs.get(key):
            values[f"{kind}:{key}:{str(attrs[key]).lower()}"] = 0.8
    return values


@dataclass
class InterestProfile:
    affinities: dict[str, float] = field(default_factory=dict)
    prices: dict[str, float] = field(default_factory=dict)
    signals: int = 0

    def affinity(self, key: str) -> float:
        return math.tanh(self.affinities.get(key, 0) / 5)

    def score(self, item: RecommendationItem) -> float:
        value = sum(strength * self.affinity(key) for key, strength in features(item).items())
        price_log = self.prices.get(category(item))
        if price_log is not None:
            value += 0.7 * math.exp(-abs(math.log(max(1, item.price_cents)) - price_log) / 0.45)
        return value


def build_profile(
    events: Sequence[InterestEvent], facts: Mapping[UUID, RecommendationItem], now: datetime
) -> InterestProfile:
    """Bound each advert/day, combining lasting tastes and a short session boost."""
    grouped: dict[tuple[UUID, str], dict[str, float]] = defaultdict(dict)
    for event in events:
        if event.listing_id not in facts:
            continue
        key = (event.listing_id, event.created_at.date().isoformat())
        if event.event_type == "completion":
            weight = -0.8 if event.value < 0.12 else max(0, event.value - 0.3) * 2
        else:
            weight = {
                "save": 4.0,
                "message": 6.0,
                "not_interested": -5.0,
                "replay": min(2, event.value) * 0.8,
            }.get(event.event_type, 0)
        age = max(0, (now - event.created_at).total_seconds())
        weight *= 2 ** (-age / (7 * 86400)) + 0.6 * 2 ** (-age / 1800)
        old = grouped[key].get(event.event_type, 0)
        if abs(weight) > abs(old):
            grouped[key][event.event_type] = weight
    profile = InterestProfile()
    prices: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for (listing_id, _), signals in grouped.items():
        weight = max(-5.0, min(6.0, sum(signals.values())))
        if not weight:
            continue
        item = facts[listing_id]
        for feature_key in features(item):
            profile.affinities[feature_key] = profile.affinities.get(feature_key, 0) + weight
        if weight > 0:
            prices[category(item)].append((math.log(max(1, item.price_cents)), weight))
        profile.signals += 1
    for kind, values in prices.items():
        profile.prices[kind] = sum(price * weight for price, weight in values) / sum(
            weight for _, weight in values
        )
    return profile


def recommend[T: RecommendationItem](
    items: Sequence[T], now: datetime, seen: set[str], profile: InterestProfile, ranker: FeedRanker
) -> list[T]:
    """Personal relevance with fresh exploration and relaxed seller/make diversity."""
    baseline = sorted(
        items,
        key=lambda item: (
            ranker.score(item, now, str(item.listing_id) in seen),
            str(item.listing_id),
        ),
        reverse=True,
    )
    ordered = sorted(
        items,
        key=lambda item: (
            0.35 * ranker.score(item, now, False)
            + profile.score(item)
            - (2 if str(item.listing_id) in seen else 0),
            str(item.listing_id),
        ),
        reverse=True,
    )
    result: list[T] = []
    remaining = {item.listing_id for item in items}
    for index in range(len(items)):
        pool = baseline if index % 5 == 4 else ordered
        choices = [item for item in pool if item.listing_id in remaining]
        recent = result[-3:]
        varied = [
            item
            for item in choices
            if sum(other.seller_id == item.seller_id for other in recent) < 2
            and sum(
                (other.make or category(other)).lower() == (item.make or category(item)).lower()
                for other in recent
            )
            < 2
        ]
        # In the mixed feed, break up long category runs when other stock is available.
        mixed = [
            item
            for item in varied
            if sum(category(other) == category(item) for other in recent) < 3
        ]
        selected = (mixed or varied or choices)[0]
        result.append(selected)
        remaining.remove(selected.listing_id)
    return result
