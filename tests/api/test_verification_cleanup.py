from datetime import UTC, datetime

import numpy as np
import pytest
from alembic.config import Config
from httpx2 import AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from app.domain import FaceEmbedder, NoFaceDetected
from app.models import CheckInRecordORM, FaceProfileORM, UserORM
from scripts import verify_week3

EXISTING_EMAIL = "existing-cleanup-test@example.com"


class VerificationEmbedder(FaceEmbedder):
    @property
    def model_name(self) -> str:
        return "buffalo_s"

    def embed(self, image_bytes: bytes) -> np.ndarray:
        if image_bytes == b"no-face":
            raise NoFaceDetected()
        assert image_bytes == b"one-face"
        return np.array([1.0, 0.0], dtype=np.float32)


@pytest.fixture
def verification_database(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'verification.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_SECRET", "cleanup-test-only-secret")
    verify_week3._reset_dependencies()
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        session.add(
            UserORM(
                email=EXISTING_EMAIL,
                hashed_password="unrelated-fixture-only",
                full_name="Existing User",
                role="user",
                created_at=datetime.now(UTC),
            )
        )
    monkeypatch.setattr("app.ml.InsightFaceEmbedder", lambda **kwargs: VerificationEmbedder())
    monkeypatch.setattr(verify_week3, "_real_face_image", lambda: b"one-face")
    monkeypatch.setattr(verify_week3, "_no_face_image", lambda: b"no-face")
    try:
        yield database_url
    finally:
        verify_week3._reset_dependencies()
        engine.dispose()


def assert_only_unrelated_data_remains(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            assert session.scalars(select(UserORM.email)).all() == [EXISTING_EMAIL]
            assert session.scalars(select(FaceProfileORM.id)).all() == []
            assert session.scalars(select(CheckInRecordORM.id)).all() == []
    finally:
        engine.dispose()


def test_verification_success_cleans_only_its_own_data(verification_database) -> None:
    result = verify_week3.run_verification(verification_database)

    assert result["check_in_status"] == "success"
    assert result["persisted_statuses"] == ["no_face", "success"]
    assert_only_unrelated_data_remains(verification_database)


@pytest.mark.parametrize("failure_stage", ["login", "face-image", "profile", "api-cleanup"])
def test_verification_failure_still_cleans_only_its_own_data(
    verification_database, monkeypatch, failure_stage
) -> None:
    message = f"simulated {failure_stage} failure"
    original_post = AsyncClient.post

    async def failing_post(client, url, *args, **kwargs):
        if (failure_stage == "login" and url == "/api/v1/auth/login") or (
            failure_stage == "profile" and url == "/api/v1/face-profiles"
        ):
            raise RuntimeError(message)
        return await original_post(client, url, *args, **kwargs)

    def failing_image():
        raise RuntimeError(message)

    async def failing_delete(*args, **kwargs):
        raise RuntimeError(message)

    monkeypatch.setattr(AsyncClient, "post", failing_post)
    if failure_stage == "face-image":
        monkeypatch.setattr(verify_week3, "_real_face_image", failing_image)
    if failure_stage == "api-cleanup":
        monkeypatch.setattr(AsyncClient, "delete", failing_delete)

    with pytest.raises(RuntimeError, match=message):
        verify_week3.run_verification(verification_database)

    assert_only_unrelated_data_remains(verification_database)
