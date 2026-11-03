from pydantic import BaseModel, Field

from app.modules.listings.schemas import ListingView


class FeedFilters(BaseModel):
    latitude: float = Field(default=53.3498, ge=-90, le=90)
    longitude: float = Field(default=-6.2603, ge=-180, le=180)
    radius_km: int = Field(default=50, ge=1, le=100)
    min_price: int = Field(default=0, ge=0)
    max_price: int = Field(default=100000000, ge=0)
    make: str | None = Field(default=None, max_length=50)
    min_year: int = Field(default=1900, ge=1900, le=2100)
    max_year: int = Field(default=2100, ge=1900, le=2100)
    region_id: str = Field(default="ie-dublin", pattern=r"^ie-dublin$")


class FeedPage(BaseModel):
    items: list[ListingView]
    next_cursor: str | None = None
    ranking: str = "heuristic-v1"
