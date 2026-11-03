import math
from datetime import datetime
from typing import Protocol
from uuid import UUID


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
