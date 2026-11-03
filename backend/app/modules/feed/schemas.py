from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.listings.schemas import ListingView


class FeedFilters(BaseModel):
    q: str | None = Field(default=None, max_length=100)
    latitude: float = Field(default=53.3498, ge=-90, le=90)
    longitude: float = Field(default=-6.2603, ge=-180, le=180)
    radius_km: int = Field(default=50, ge=1, le=100)
    min_price: int = Field(default=0, ge=0)
    max_price: int = Field(default=100000000, ge=0)
    make: str | None = Field(default=None, max_length=50)
    min_year: int = Field(default=1900, ge=1900, le=2100)
    max_year: int = Field(default=2100, ge=1900, le=2100)
    max_mileage: int = Field(default=3000000, ge=0, le=3000000)
    fuel: Literal["petrol", "diesel", "electric", "hybrid"] | None = None
    transmission: Literal["manual", "automatic"] | None = None
    sort: Literal["recommended", "newest", "price_asc", "price_desc"] = "recommended"
    region_id: str = Field(default="ie-dublin", pattern=r"^ie-dublin$")

    @field_validator("q", "make")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        cleaned = " ".join((value or "").split()).lower()
        if len(cleaned.split()) > 8:
            raise ValueError("Use at most eight search words.")
        return cleaned or None

    @model_validator(mode="after")
    def valid_ranges(self) -> Self:
        if self.min_price > self.max_price or self.min_year > self.max_year:
            raise ValueError("Minimum values must not exceed maximum values.")
        return self


class FeedRequest(FeedFilters):
    cursor: str | None = Field(default=None, max_length=4096)


class FeedOptions(BaseModel):
    makes: list[str]


class FeedPage(BaseModel):
    items: list[ListingView]
    next_cursor: str | None = None
    ranking: str = "heuristic-v1"
