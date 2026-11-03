from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.listings.categories import ATTRIBUTE_MODELS, Category
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
    price_cents: int = Field(gt=0, le=2000000000)
    area: str = Field(min_length=2, max_length=100)
    latitude: float = Field(ge=53.05, le=53.65)
    longitude: float = Field(ge=-6.65, le=-5.95)
    category: Category = "cars"
    region_id: Literal["ie-dublin"] = "ie-dublin"
    rights_confirmed: Literal[True]
    car: CarInput | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def category_facts(self) -> Self:
        if self.category == "cars" and self.car is None:
            raise ValueError("Car listings need car details.")
        if self.category != "cars" and self.car is not None:
            raise ValueError("Car details only belong to car listings.")
        self.attributes = (
            ATTRIBUTE_MODELS[self.category]
            .model_validate(self.attributes)
            .model_dump(exclude_none=True)
        )
        return self


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
    car: CarInput | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
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
