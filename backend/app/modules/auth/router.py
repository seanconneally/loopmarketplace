from fastapi import APIRouter, Request, Response

from app.core.config import settings
from app.core.dependencies import CurrentUser, Session, same_origin
from app.core.errors import require
from app.modules.auth.schemas import AuthView, ChallengeView, OtpRequest, OtpVerify, TicketView
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def set_refresh(response: Response, token: str) -> None:
    response.set_cookie(
        "refresh",
        token,
        httponly=True,
        secure=settings().app_env == "production",
        samesite="strict",
        path="/api/v1/auth",
        max_age=settings().refresh_days * 86400,
    )
    response.headers["Cache-Control"] = "no-store"


@router.post("/otp/request", response_model=ChallengeView)
async def challenge(data: OtpRequest, request: Request, session: Session) -> ChallengeView:
    return await AuthService(session).challenge(
        data.phone, request.client.host if request.client else "unknown"
    )


@router.post("/otp/verify", response_model=AuthView)
async def verify(
    data: OtpVerify, request: Request, response: Response, session: Session
) -> AuthView:
    same_origin(request)
    result, refresh = await AuthService(session).verify(data.phone, data.code)
    set_refresh(response, refresh)
    return result


@router.post("/refresh", response_model=AuthView)
async def refresh(request: Request, response: Response, session: Session) -> AuthView:
    same_origin(request)
    require(request.cookies.get("refresh"), 401, "invalid_session", "Sign in again.")
    result, token = await AuthService(session).refresh(request.cookies["refresh"])
    set_refresh(response, token)
    return result


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, session: Session) -> None:
    same_origin(request)
    await AuthService(session).logout(request.cookies.get("refresh", ""))
    response.delete_cookie("refresh", path="/api/v1/auth")


@router.post("/ws-ticket", response_model=TicketView)
async def ticket(request: Request, session: Session, user: CurrentUser) -> TicketView:
    credentials = request.headers.get("authorization", "").removeprefix("Bearer ")
    _, family = await AuthService(session).authenticate(credentials)
    return TicketView(ticket=await AuthService(session).ticket(user, family))
