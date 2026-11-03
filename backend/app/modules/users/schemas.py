from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    role: str
    adult_declared: bool
    analytics_consent: bool


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    adult_declared: bool
    analytics_consent: bool = False


class SellerView(BaseModel):
    id: UUID
    name: str
    dealer_verified: bool
