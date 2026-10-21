from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUserDependency, UserServiceDependency
from app.core.config import get_settings
from app.core.security import create_access_token
from app.schemas import TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: UserServiceDependency,
) -> TokenResponse:
    user = service.authenticate(
        email=form.username,
        password=form.password,
    )
    settings = get_settings()
    token = create_access_token(
        user_id=user.id,
        role=user.role,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUserDependency):
    return current_user
