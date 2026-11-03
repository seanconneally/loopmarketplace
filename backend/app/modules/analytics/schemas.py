from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EventInput(BaseModel):
    client_event_id: UUID
    listing_id: UUID
    event_type: Literal["impression", "watch", "save", "message"]
    value: float = Field(default=1, ge=0, le=3600)


class EventBatch(BaseModel):
    events: list[EventInput] = Field(min_length=1, max_length=100)
