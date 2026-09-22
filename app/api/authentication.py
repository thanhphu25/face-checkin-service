from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
)
from starlette.concurrency import run_in_threadpool
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.domain.entities import User
from app.domain.errors import InvalidToken
from app.repositories import SQLAlchemyUserRepository


class AuthenticatedUser(BaseUser):
    """Expose the current domain user through Starlette's request.user interface."""

    def __init__(self, user: User) -> None:
        self.user = user

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.user.full_name


class JWTAuthenticationBackend(AuthenticationBackend):
    def __init__(self, session_factory_provider: Callable[[], sessionmaker[Session]]) -> None:
        self._session_factory_provider = session_factory_provider

    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, BaseUser] | None:
        authorization = conn.headers.get("Authorization")
        if authorization is None:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.casefold() != "bearer":
            return None

        try:
            user = await run_in_threadpool(self._authenticate_token, token)
        except InvalidToken as exc:
            raise AuthenticationError(str(exc)) from exc
        return AuthCredentials(["authenticated"]), AuthenticatedUser(user)

    def _authenticate_token(self, token: str) -> User:
        settings = get_settings()
        claims = decode_access_token(
            token=token,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        session_factory = self._session_factory_provider()
        # Create, use and close the read session in the same worker thread. Only a
        # domain entity leaves this scope; endpoint writes use their own session.
        with session_factory() as session:
            user = SQLAlchemyUserRepository(session).get(claims.user_id)
        if user is None:
            raise InvalidToken()
        return user


def authentication_error_response(_conn: HTTPConnection, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc), "error": "InvalidToken"},
        headers={"WWW-Authenticate": "Bearer"},
    )
