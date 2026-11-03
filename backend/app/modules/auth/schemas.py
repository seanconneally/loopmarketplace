from pydantic import BaseModel, Field

from app.modules.users.schemas import UserView


class OtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")


class OtpVerify(OtpRequest):
    code: str = Field(pattern=r"^\d{6}$")


class ChallengeView(BaseModel):
    message: str
    development_code: str | None = None


class AuthView(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView


class TicketView(BaseModel):
    ticket: str
    expires_in: int = 30
