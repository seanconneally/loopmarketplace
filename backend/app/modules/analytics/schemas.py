from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.core.db import utcnow


class EventInput(BaseModel):
    client_event_id: UUID
    listing_id: UUID
    event_type: Literal[
        "impression", "watch", "completion", "save", "message", "not_interested", "replay"
    ]
    value: float = Field(default=1, ge=0, le=3600)
    occurred_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def bounded_completion(self) -> Self:
        if self.event_type == "completion" and self.value > 1:
            raise ValueError("Completion is a fraction between zero and one.")
        if self.event_type == "replay" and self.value > 2:
            raise ValueError("At most two replays per receipt.")
        if self.occurred_at and not -5 <= (utcnow() - self.occurred_at).total_seconds() <= 60:
            raise ValueError("Playback receipts must be recent.")
        return self


class InterestEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    listing_id: UUID
    event_type: str
    value: float
    created_at: datetime


class EventBatch(BaseModel):
    events: list[EventInput] = Field(min_length=1, max_length=100)
