from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import CheckInRecord, CheckInStatus, FaceProfile, Role, User
from app.models import FaceProfileORM
from app.repositories import (
    SQLAlchemyCheckInRepository,
    SQLAlchemyFaceProfileRepository,
    SQLAlchemyUserRepository,
)


def _add_user(
    repository: SQLAlchemyUserRepository,
    email: str = "user@example.com",
    role: Role = Role.USER,
) -> User:
    return repository.add(
        User(
            id=None,
            email=email,
            hashed_password="hashed-password",
            role=role,
            full_name="Example User",
            created_at=datetime(2026, 9, 21, 8, tzinfo=UTC),
        )
    )


def test_user_repository_crud(session: Session) -> None:
    repository = SQLAlchemyUserRepository(session)
    saved = _add_user(repository, role=Role.ADMIN)
    second = _add_user(repository, email="second@example.com")

    assert saved.id is not None
    assert saved.role is Role.ADMIN
    assert repository.get(saved.id) == saved
    assert repository.get_by_email(saved.email) == saved
    assert repository.list_all() == [saved, second]

    repository.delete(saved.id)
    assert repository.get(saved.id) is None
    repository.delete(saved.id)


def test_user_repository_enforces_unique_email(session: Session) -> None:
    repository = SQLAlchemyUserRepository(session)
    _add_user(repository)

    with pytest.raises(IntegrityError), session.begin_nested():
        _add_user(repository)


def test_face_profile_repository_crud_and_embedding_mapping(session: Session) -> None:
    user = _add_user(SQLAlchemyUserRepository(session))
    repository = SQLAlchemyFaceProfileRepository(session)
    embedding = np.array([0.6, 0.8], dtype=np.float64)

    saved = repository.add(
        FaceProfile(
            id=None,
            user_id=user.id,
            embedding=embedding,
            model_name="buffalo_s",
            created_at=datetime(2026, 9, 21, 9, tzinfo=UTC),
        )
    )

    assert saved.id is not None
    assert saved.embedding.dtype == np.float32
    expected = embedding.astype("<f4")
    np.testing.assert_array_equal(saved.embedding, expected)
    row = session.scalar(select(FaceProfileORM).where(FaceProfileORM.id == saved.id))
    assert row is not None
    assert row.embedding_dim == expected.size
    assert row.embedding == expected.tobytes()
    assert row.model_name == "buffalo_s"
    assert [profile.id for profile in repository.list_all()] == [saved.id]
    assert [profile.id for profile in repository.list_by_user(user.id)] == [saved.id]

    repository.delete(saved.id)
    assert repository.get(saved.id) is None


def test_face_profile_repository_rejects_invalid_embedding(session: Session) -> None:
    user = _add_user(SQLAlchemyUserRepository(session))
    repository = SQLAlchemyFaceProfileRepository(session)

    with pytest.raises(ValueError, match="one-dimensional"):
        repository.add(
            FaceProfile(
                id=None,
                user_id=user.id,
                embedding=np.empty((0, 2), dtype=np.float32),
                model_name="buffalo_s",
                created_at=datetime.now(UTC),
            )
        )


def test_check_in_repository_crud_status_mapping(session: Session) -> None:
    user = _add_user(SQLAlchemyUserRepository(session))
    profile = SQLAlchemyFaceProfileRepository(session).add(
        FaceProfile(
            id=None,
            user_id=user.id,
            embedding=np.array([0.6, 0.8], dtype=np.float32),
            model_name="buffalo_s",
            created_at=datetime(2026, 9, 21, 9, tzinfo=UTC),
        )
    )
    repository = SQLAlchemyCheckInRepository(session)
    checkin_time = datetime(2026, 9, 21, 10, tzinfo=UTC)
    success = repository.add(
        CheckInRecord(
            id=None,
            user_id=user.id,
            matched_face_profile_id=profile.id,
            checkin_time=checkin_time,
            similarity_score=0.91,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )
    unmatched = repository.add(
        CheckInRecord(
            id=None,
            user_id=None,
            matched_face_profile_id=None,
            checkin_time=checkin_time + timedelta(hours=1),
            similarity_score=0.2,
            threshold=0.4,
            status=CheckInStatus.UNMATCHED,
        )
    )
    no_face = repository.add(
        CheckInRecord(
            id=None,
            user_id=None,
            matched_face_profile_id=None,
            checkin_time=checkin_time + timedelta(hours=2),
            similarity_score=None,
            threshold=0.4,
            status=CheckInStatus.NO_FACE,
        )
    )

    assert repository.get(success.id) == success
    assert [record.status for record in repository.list()] == [
        CheckInStatus.NO_FACE,
        CheckInStatus.UNMATCHED,
        CheckInStatus.SUCCESS,
    ]

    repository.delete(unmatched.id)
    assert repository.get(unmatched.id) is None
    assert repository.get(no_face.id) == no_face


def test_check_in_repository_filters_newest_first_and_limits(session: Session) -> None:
    users = SQLAlchemyUserRepository(session)
    first_user = _add_user(users)
    second_user = _add_user(users, email="second@example.com")
    repository = SQLAlchemyCheckInRepository(session)
    first_time = datetime(2026, 9, 21, 10, tzinfo=UTC)

    first = repository.add(
        CheckInRecord(
            id=None,
            user_id=first_user.id,
            matched_face_profile_id=None,
            checkin_time=first_time,
            similarity_score=0.91,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )
    second = repository.add(
        CheckInRecord(
            id=None,
            user_id=second_user.id,
            matched_face_profile_id=None,
            checkin_time=first_time + timedelta(hours=1),
            similarity_score=0.92,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )
    latest = repository.add(
        CheckInRecord(
            id=None,
            user_id=first_user.id,
            matched_face_profile_id=None,
            checkin_time=first_time + timedelta(hours=2),
            similarity_score=0.93,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )

    assert [record.id for record in repository.list()] == [latest.id, second.id, first.id]
    assert [record.id for record in repository.list(user_id=first_user.id)] == [
        latest.id,
        first.id,
    ]
    assert repository.list(start=first_time + timedelta(minutes=30), limit=1) == [latest]
    assert repository.list(end=first_time + timedelta(minutes=30)) == [first]
    assert repository.list(
        start=first_time + timedelta(hours=1),
        end=first_time + timedelta(hours=2),
    ) == [second]
    with pytest.raises(ValueError, match="positive"):
        repository.list(limit=0)


def test_foreign_keys_cascade_profiles_and_preserve_history(session: Session) -> None:
    users = SQLAlchemyUserRepository(session)
    profiles = SQLAlchemyFaceProfileRepository(session)
    checkins = SQLAlchemyCheckInRepository(session)
    user = _add_user(users)
    profile = profiles.add(
        FaceProfile(
            id=None,
            user_id=user.id,
            embedding=np.array([0.6, 0.8], dtype=np.float32),
            model_name="buffalo_s",
            created_at=datetime(2026, 9, 21, 9, tzinfo=UTC),
        )
    )
    record = checkins.add(
        CheckInRecord(
            id=None,
            user_id=user.id,
            matched_face_profile_id=profile.id,
            checkin_time=datetime(2026, 9, 21, 10, tzinfo=UTC),
            similarity_score=0.91,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )

    profiles.delete(profile.id)
    session.expire_all()
    after_profile_delete = checkins.get(record.id)
    assert after_profile_delete is not None
    assert after_profile_delete.user_id == user.id
    assert after_profile_delete.matched_face_profile_id is None

    replacement = profiles.add(
        FaceProfile(
            id=None,
            user_id=user.id,
            embedding=np.array([1.0, 0.0], dtype=np.float32),
            model_name="buffalo_s",
            created_at=datetime(2026, 9, 21, 11, tzinfo=UTC),
        )
    )
    later_record = checkins.add(
        CheckInRecord(
            id=None,
            user_id=user.id,
            matched_face_profile_id=replacement.id,
            checkin_time=datetime(2026, 9, 21, 12, tzinfo=UTC),
            similarity_score=0.95,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )

    users.delete(user.id)
    session.expire_all()

    assert users.get(user.id) is None
    assert profiles.get(replacement.id) is None
    preserved = checkins.get(record.id)
    preserved_later = checkins.get(later_record.id)
    assert preserved is not None and preserved.user_id is None
    assert preserved_later is not None
    assert preserved_later.user_id is None
    assert preserved_later.matched_face_profile_id is None


def test_database_foreign_keys_are_active(session: Session) -> None:
    bind = session.get_bind()
    if bind.dialect.name == "sqlite":
        assert session.scalar(text("PRAGMA foreign_keys")) == 1
        return

    user_foreign_keys = inspect(bind).get_foreign_keys("check_in_records")
    assert {foreign_key["options"].get("ondelete") for foreign_key in user_foreign_keys} == {
        "SET NULL"
    }
