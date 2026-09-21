import asyncio
from datetime import UTC, datetime

from app.api.deps import get_current_user, get_user_service
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.domain import AuthenticationFailed, Role, User
from app.main import create_app

NOW = datetime(2026, 9, 21, 10, tzinfo=UTC)
SECRET = "api-test-secret-that-is-not-used-outside-tests"


class AuthenticationServiceSpy:
    def __init__(self) -> None:
        self.user = User(7, "person@example.com", "must-not-leak", Role.USER, "Person", NOW)
        self.attempts: list[tuple[str, str]] = []

    def authenticate(self, *, email: str, password: str) -> User:
        normalized_email = email.strip().casefold()
        self.attempts.append((normalized_email, password))
        if normalized_email != self.user.email or password != "correct-password":
            raise AuthenticationFailed()
        return self.user


def test_login_returns_bearer_jwt_and_me_never_exposes_password_hash(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRET)
    get_settings.cache_clear()
    service = AuthenticationServiceSpy()
    app = create_app()
    app.dependency_overrides[get_user_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: service.user

    async def exercise_auth():
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                data={"username": " PERSON@EXAMPLE.COM ", "password": "correct-password"},
            )
            me = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            )
        return login, me

    login, me = asyncio.run(exercise_auth())

    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    claims = decode_access_token(
        token=login.json()["access_token"], secret=SECRET, algorithm="HS256"
    )
    assert claims.user_id == 7
    assert claims.role is Role.USER
    assert service.attempts == [("person@example.com", "correct-password")]
    assert me.status_code == 200
    assert me.json()["email"] == "person@example.com"
    assert "hashed_password" not in me.json()


def test_login_failure_has_one_message_for_unknown_email_and_wrong_password(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRET)
    get_settings.cache_clear()
    service = AuthenticationServiceSpy()
    app = create_app()
    app.dependency_overrides[get_user_service] = lambda: service

    async def attempt_logins():
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            wrong_password = await client.post(
                "/api/v1/auth/login",
                data={"username": "person@example.com", "password": "wrong-password"},
            )
            missing_email = await client.post(
                "/api/v1/auth/login",
                data={"username": "missing@example.com", "password": "wrong-password"},
            )
        return wrong_password, missing_email

    wrong_password, missing_email = asyncio.run(attempt_logins())

    assert wrong_password.status_code == missing_email.status_code == 401
    assert (
        wrong_password.json()
        == missing_email.json()
        == {
            "detail": "Incorrect email or password",
            "error": "AuthenticationFailed",
        }
    )
    assert wrong_password.headers["www-authenticate"] == "Bearer"
