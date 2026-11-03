from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportInput(BaseModel):
    target_type: Literal["listing", "user", "message"]
    target_id: UUID
    reason: str = Field(min_length=5, max_length=1000)


class BlockInput(BaseModel):
    user_id: UUID


class ReportView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    target_type: str
    target_id: UUID
    reason: str
    status: str
    created_at: datetime


class ReportPage(BaseModel):
    items: list[ReportView]
    next_cursor: str | None = None


class ActionInput(BaseModel):
    target_type: Literal["listing", "user"]
    target_id: UUID
    action: Literal["approve", "remove", "suspend"]
    reason: str = Field(min_length=5, max_length=1000)
