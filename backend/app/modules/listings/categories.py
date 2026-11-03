"""Category-specific facts; shared listing/media/seller lifecycle stays universal."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["cars", "homes", "golf", "other"]


class Attributes(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HomeAttributes(Attributes):
    property_type: Literal["house", "apartment", "land", "other"] = "house"
    bedrooms: int | None = Field(default=None, ge=0, le=100)
    bathrooms: int | None = Field(default=None, ge=0, le=100)
    floor_area_m2: float | None = Field(default=None, gt=0, le=1000000)


class ItemAttributes(Attributes):
    brand: str = Field(default="", max_length=80)
    condition: Literal["new", "like_new", "good", "fair"] = "good"


class GolfAttributes(ItemAttributes):
    club_type: Literal["driver", "irons", "putter", "wedge", "set", "other"] = "other"
    hand: Literal["right", "left", "either"] = "right"


ATTRIBUTE_MODELS: dict[str, type[Attributes]] = {
    "cars": Attributes,
    "homes": HomeAttributes,
    "golf": GolfAttributes,
    "other": ItemAttributes,
}
