from fastapi import APIRouter

from app.core.dependencies import CurrentUser, Session
from app.modules.users.schemas import ProfileUpdate, UserView
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserView)
async def me(session: Session, user: CurrentUser) -> UserView:
    return UserView.model_validate(await UserService(session).active(user))


@router.patch("/me", response_model=UserView)
async def update(data: ProfileUpdate, session: Session, user: CurrentUser) -> UserView:
    return await UserService(session).update(user, data)
