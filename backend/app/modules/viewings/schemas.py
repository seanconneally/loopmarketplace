from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ViewingInput(BaseModel):
    conversation_id: UUID
    starts_at: AwareDatetime
    place: str = Field(min_length=5, max_length=300)


class ViewingResponse(BaseModel):
    action: Literal["accept", "decline", "cancel", "counter"]
    revision: int = Field(ge=1)
    starts_at: AwareDatetime | None = None
    place: str | None = Field(default=None, min_length=5, max_length=300)


class ViewingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    proposed_by: UUID
    starts_at: datetime
    place: str
    status: str
    revision: int
    history: list[dict[str, Any]]


class ViewingPage(BaseModel):
    items: list[ViewingView]
    next_cursor: str | None = None
