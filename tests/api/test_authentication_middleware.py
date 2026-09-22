import asyncio
from datetime import UTC, datetime, timedelta
from threading import get_ident

import pytest
from alembic.config import Config
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient

from alembic import command
from app.api import authentication
from app.api.deps import (
    AdminUserDependency,
    CurrentUserDependency,
    get_check_in_service,
    get_engine,
    get_session_factory,
)
from app.core.config import get_settings
from app.core.security import create_access_token
from app.domain import Role, UnmatchedFace, User
from app.main import create_app
from app.repositories import SQLAlchemyUserRepository

SECRET = "middleware-test-only-secret-not-used-outside-tests"


def _reset_dependencies() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def authenticated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'authentication.db'}")
    _reset_dependencies()
    command.upgrade(Config("alembic.ini"), "head")
    with get_session_factory()() as session:
        user = SQLAlchemyUserRepository(session).add(
            User(None, "admin@example.test", "unused", Role.ADMIN, "Admin", datetime.now(UTC))
        )
        session.commit()
    try:
        yield create_app(), user
    finally:
        _reset_dependencies()


def _token(user_id: int, *, secret: str = SECRET, expired: bool = False) -> str:
    return create_access_token(
        user_id=user_id,
        role=Role.ADMIN,
        secret=secret,
        algorithm="HS256",
        expires_delta=timedelta(minutes=-1 if expired else 30),
    )


def test_middleware_authenticates_once_and_reuses_the_user(authenticated_app, monkeypatch):
    app, user = authenticated_app
    calls = {"decode": 0, "lookup": 0}
    lookup_threads = []
    decode = authentication.decode_access_token
    lookup = SQLAlchemyUserRepository.get

    def counted_decode(**kwargs):
        calls["decode"] += 1
        return decode(**kwargs)

    def counted_lookup(repository, user_id):
        calls["lookup"] += 1
        lookup_threads.append(get_ident())
        return lookup(repository, user_id)

    monkeypatch.setattr(authentication, "decode_access_token", counted_decode)
    monkeypatch.setattr(SQLAlchemyUserRepository, "get", counted_lookup)

    @app.get("/test-shared-principal")
    def shared_principal(current: CurrentUserDependency, admin: AdminUserDependency):
        return {"id": current.id, "same_user": current is admin}

    event_loop_thread = get_ident()

    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(
                "/test-shared-principal", headers={"Authorization": f"Bearer {_token(user.id)}"}
            )

    response = asyncio.run(exercise())
    assert response.status_code == 200
    assert response.json() == {"id": user.id, "same_user": True}
    assert calls == {"decode": 1, "lookup": 1}
    assert lookup_threads[0] != event_loop_thread


@pytest.mark.parametrize("kind", ["malformed", "empty", "wrong_signature", "expired", "deleted"])
def test_middleware_returns_json_401_for_invalid_credentials(authenticated_app, kind):
    app, user = authenticated_app
    token = _token(user.id)
    if kind == "malformed":
        token = "broken.token.value"
    elif kind == "empty":
        token = ""
    elif kind == "wrong_signature":
        token = _token(user.id, secret="another-test-only-signing-secret")
    elif kind == "expired":
        token = _token(user.id, expired=True)
    elif kind == "deleted":
        with get_session_factory()() as session:
            SQLAlchemyUserRepository(session).delete(user.id)
            session.commit()

    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    response = asyncio.run(exercise())
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": "Could not validate credentials",
        "error": "InvalidToken",
    }


def test_middleware_uses_current_database_role(authenticated_app):
    app, user = authenticated_app
    token = _token(user.id)
    with get_session_factory()() as session:
        from app.models import UserORM

        session.get(UserORM, user.id).role = Role.USER.value
        session.commit()

    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})

    response = asyncio.run(exercise())
    assert response.status_code == 403
    assert response.json()["error"] == "PermissionDenied"


def test_anonymous_public_routes_do_not_authenticate_or_query_users(authenticated_app, monkeypatch):
    app, _ = authenticated_app

    def unexpected_authentication(*args, **kwargs):
        pytest.fail("Anonymous requests must not decode tokens or look up users")

    monkeypatch.setattr(authentication, "decode_access_token", unexpected_authentication)
    monkeypatch.setattr(SQLAlchemyUserRepository, "get", unexpected_authentication)

    class UnmatchedCheckIn:
        def check_in(self, image_bytes):
            raise UnmatchedFace(0.2, record_id=7)

    app.dependency_overrides[get_check_in_service] = UnmatchedCheckIn

    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            responses = [await client.get(path) for path in ("/health", "/docs", "/openapi.json")]
            responses.append(await client.post("/api/v1/auth/login", data={}))
            responses.append(
                await client.post(
                    "/api/v1/checkins", files={"image": ("face.png", b"image", "image/png")}
                )
            )
            responses.append(await client.get("/api/v1/auth/me"))
            return responses

    responses = asyncio.run(exercise())
    assert [response.status_code for response in responses] == [200, 200, 200, 422, 404, 401]
    assert responses[-2].json()["record_id"] == 7
    assert responses[-1].headers["www-authenticate"] == "Bearer"


def test_supplied_invalid_bearer_is_rejected_even_on_public_routes(authenticated_app):
    app, _ = authenticated_app

    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/health", headers={"Authorization": "Bearer invalid"})

    assert asyncio.run(exercise()).status_code == 401


def test_dependency_requires_a_principal_from_the_middleware():
    # A syntactically present header alone must not authenticate a request.
    app = FastAPI()

    @app.get("/protected")
    def protected(user: CurrentUserDependency):
        return {"id": user.id}

    from starlette.authentication import AuthenticationBackend
    from starlette.middleware.authentication import AuthenticationMiddleware

    from app.api.authentication import authentication_error_response
    from app.api.errors import register_error_handlers

    class AnonymousBackend(AuthenticationBackend):
        async def authenticate(self, conn):
            return None

    register_error_handlers(app)
    app.add_middleware(
        AuthenticationMiddleware,
        backend=AnonymousBackend(),
        on_error=authentication_error_response,
    )

    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/protected", headers={"Authorization": "Bearer unverified"})

    assert asyncio.run(exercise()).status_code == 401
