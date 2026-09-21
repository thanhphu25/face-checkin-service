import asyncio
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_engine, get_session, get_session_factory
from app.core.config import get_settings
from app.core.security import PBKDF2PasswordHasher
from app.domain import InvalidImage, NoFaceDetected, UnmatchedFace, UserNotFound
from app.main import create_app
from app.models import Base, UserORM


def _reset_database_dependencies() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_password_hasher_never_stores_plaintext_and_verifies() -> None:
    hasher = PBKDF2PasswordHasher()

    password_hash = hasher.hash("strong-password")

    assert "strong-password" not in password_hash
    assert hasher.verify("strong-password", password_hash)
    assert not hasher.verify("wrong-password", password_hash)
    assert not hasher.verify("strong-password", "broken-hash")


def test_domain_errors_are_mapped_to_400_404_and_422(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    app = create_app()

    @app.get("/test-errors/{kind}")
    def raise_error(kind: str) -> None:
        errors = {
            "bad-request": InvalidImage("bad image"),
            "not-found": UserNotFound("missing user"),
            "unprocessable": NoFaceDetected("missing face"),
            "unmatched": UnmatchedFace(0.2, record_id=9),
        }
        raise errors[kind]

    async def request_errors() -> list[tuple[int, dict]]:
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = [
                await client.get(f"/test-errors/{kind}")
                for kind in ("bad-request", "not-found", "unprocessable", "unmatched")
            ]
        return [(response.status_code, response.json()) for response in responses]

    responses = asyncio.run(request_errors())

    assert [status for status, _ in responses] == [400, 404, 422, 404]
    assert responses[-1][1] == {
        "detail": "No registered face matched the image",
        "error": "UnmatchedFace",
        "record_id": 9,
        "best_score": 0.2,
    }


def test_session_commits_expected_domain_error_audit_record(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{(tmp_path / 'composition.db').as_posix()}"
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("DATABASE_URL", database_url)
    _reset_database_dependencies()
    Base.metadata.create_all(get_engine())
    app = create_app()

    @app.post("/test-expected-error")
    def create_then_fail(session: Annotated[Session, Depends(get_session)]) -> None:
        session.add(
            UserORM(
                email="persisted@example.com",
                hashed_password="hash",
                role="user",
                full_name="Persisted",
                created_at=datetime.now(UTC),
            )
        )
        session.flush()
        raise NoFaceDetected("expected failure")

    async def request_error() -> int:
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return (await client.post("/test-expected-error")).status_code

    assert asyncio.run(request_error()) == 422
    with get_session_factory()() as session:
        assert session.scalar(select(UserORM.email)) == "persisted@example.com"

    _reset_database_dependencies()
