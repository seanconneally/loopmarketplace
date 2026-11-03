"""Documented WebSocket envelopes. REST remains authoritative for replay."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.messaging.schemas import MessageView
from app.modules.viewings.schemas import ViewingView


class MessageData(BaseModel):
    conversation_id: UUID
    message: MessageView


class ReadData(BaseModel):
    conversation_id: UUID
    reader_id: UUID
    message_id: UUID
    read_at: datetime


class ViewingData(BaseModel):
    viewing: ViewingView


class ListingData(BaseModel):
    listing_id: UUID
    status: str


class BlockData(BaseModel):
    target_id: UUID


class MessageCreated(BaseModel):
    type: Literal["message.created"]
    data: MessageData


class MessageRead(BaseModel):
    type: Literal["message.read"]
    data: ReadData


class ViewingUpdated(BaseModel):
    type: Literal["viewing.updated"]
    data: ViewingData


class ListingStatus(BaseModel):
    type: Literal["listing.status"]
    data: ListingData


class BlockChanged(BaseModel):
    type: Literal["block.changed"]
    data: BlockData


class Heartbeat(BaseModel):
    type: Literal["heartbeat"]
    data: dict[str, str]


WebSocketEvent = Annotated[
    MessageCreated | MessageRead | ViewingUpdated | ListingStatus | BlockChanged | Heartbeat,
    Field(discriminator="type"),
]
