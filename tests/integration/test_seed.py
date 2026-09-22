import pytest
from sqlalchemy.orm import Session

from app.core.security import Argon2PasswordHasher
from app.domain import CheckInStatus, Role
from app.repositories import SQLAlchemyCheckInRepository, SQLAlchemyUserRepository
from scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD_ENV, USER_EMAIL, USER_PASSWORD_ENV, seed

ADMIN_PASSWORD = "seed-test-only-admin-password"
USER_PASSWORD = "seed-test-only-user-password"


@pytest.fixture
def seed_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADMIN_PASSWORD_ENV, ADMIN_PASSWORD)
    monkeypatch.setenv(USER_PASSWORD_ENV, USER_PASSWORD)


def test_seed_creates_sample_accounts_and_history(session: Session, seed_passwords: None) -> None:
    summary = seed(session, with_face_profile=False)
    session.flush()

    users = SQLAlchemyUserRepository(session)
    admin = users.get_by_email(ADMIN_EMAIL)
    member = users.get_by_email(USER_EMAIL)
    assert admin is not None and member is not None
    assert admin.role is Role.ADMIN
    assert member.role is Role.USER
    assert summary["admin_id"] == admin.id
    assert summary["user_id"] == member.id
    assert summary["face_profile_id"] is None

    hasher = Argon2PasswordHasher()
    assert admin.hashed_password not in (ADMIN_PASSWORD, "")
    assert hasher.verify(ADMIN_PASSWORD, admin.hashed_password)
    assert hasher.verify(USER_PASSWORD, member.hashed_password)
    assert not hasher.verify(USER_PASSWORD, admin.hashed_password)

    history = SQLAlchemyCheckInRepository(session).list(limit=50)
    assert [record.status for record in history] == [
        CheckInStatus.NO_FACE,
        CheckInStatus.UNMATCHED,
        CheckInStatus.SUCCESS,
    ]
    successful = history[-1]
    assert successful.user_id == member.id
    assert successful.similarity_score is not None
    assert history[0].similarity_score is None


def test_seed_is_idempotent(session: Session, seed_passwords: None) -> None:
    first = seed(session, with_face_profile=False)
    session.flush()
    second = seed(session, with_face_profile=False)
    session.flush()

    assert second["admin_id"] == first["admin_id"]
    assert second["user_id"] == first["user_id"]
    assert second["history_created"] == 0
    assert len(SQLAlchemyUserRepository(session).list_all()) == 2
    assert len(SQLAlchemyCheckInRepository(session).list(limit=50)) == 3


@pytest.mark.parametrize("password", ["", "   ", "too-short"])
def test_seed_refuses_missing_or_weak_passwords(
    session: Session, monkeypatch: pytest.MonkeyPatch, password: str
) -> None:
    monkeypatch.setenv(ADMIN_PASSWORD_ENV, password)
    monkeypatch.setenv(USER_PASSWORD_ENV, USER_PASSWORD)

    with pytest.raises(SystemExit, match=ADMIN_PASSWORD_ENV):
        seed(session, with_face_profile=False)
