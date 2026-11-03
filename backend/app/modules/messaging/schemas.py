from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationInput(BaseModel):
    listing_id: UUID


class ConversationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    listing_id: UUID
    buyer_id: UUID
    seller_id: UUID
    last_message_at: datetime | None
    listing_title: str = "Listing"
    other_name: str = "Member"


class ConversationPage(BaseModel):
    items: list[ConversationView]
    next_cursor: str | None = None


class MessageInput(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class ReadInput(BaseModel):
    message_id: UUID


class MessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    body: str
    message_type: str
    viewing_id: UUID | None
    warnings: list[str]
    created_at: datetime
    read_at: datetime | None


class MessagePage(BaseModel):
    items: list[MessageView]
    next_cursor: str | None = None
