from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.media.schemas import OwnerMediaView
from app.modules.users.schemas import SellerView


class CarInput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    make: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=1900, le=2100)
    mileage_km: int = Field(ge=0, le=3000000)
    fuel: Literal["petrol", "diesel", "electric", "hybrid"]
    transmission: Literal["manual", "automatic"]


class ListingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=3000)
    price_cents: int = Field(gt=0, le=100000000)
    area: str = Field(min_length=2, max_length=100)
    latitude: float = Field(ge=53.05, le=53.65)
    longitude: float = Field(ge=-6.65, le=-5.95)
    category: Literal["cars"] = "cars"
    region_id: Literal["ie-dublin"] = "ie-dublin"
    rights_confirmed: Literal[True]
    car: CarInput


class ListingView(BaseModel):
    id: UUID
    title: str
    description: str
    price_cents: int
    currency: str
    status: str
    area: str
    category: str
    region_id: str
    car: CarInput
    seller: SellerView
    playback_url: str | None = None
    poster_url: str | None = None
    duration: float | None = None
    published_at: datetime | None = None
    saved: bool = False
    has_audio: bool = False


class ListingUpdate(ListingCreate):
    revision: int = Field(ge=1)


class ListingAction(BaseModel):
    revision: int = Field(ge=1)


class SellerListingView(ListingView):
    revision: int
    is_paused: bool
    latitude: float
    longitude: float
    created_at: datetime
    media: OwnerMediaView | None = None


class SellerListingPage(BaseModel):
    items: list[SellerListingView]
    next_cursor: str | None = None


class ListingPage(BaseModel):
    items: list[ListingView]
    next_cursor: str | None = None
