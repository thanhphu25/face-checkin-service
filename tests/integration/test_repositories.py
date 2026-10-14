from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain import CheckInRecord, CheckInStatus, FaceProfile, Role, User
from app.models import Base
from app.repositories import (
    SQLAlchemyCheckInRepository,
    SQLAlchemyFaceProfileRepository,
    SQLAlchemyUserRepository,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _add_user(repository: SQLAlchemyUserRepository, email: str = "user@example.com") -> User:
    return repository.add(
        User(
            id=None,
            email=email,
            hashed_password="hashed-password",
            role=Role.USER,
            full_name="Example User",
            created_at=datetime(2026, 9, 21, 8, tzinfo=UTC),
        )
    )


def test_user_repository_crud(session: Session) -> None:
    repository = SQLAlchemyUserRepository(session)
    saved = _add_user(repository)

    assert saved.id is not None
    assert repository.get(saved.id) == saved
    assert repository.get_by_email(saved.email) == saved
    assert repository.list_all() == [saved]

    repository.delete(saved.id)
    assert repository.get(saved.id) is None
    repository.delete(saved.id)


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
    np.testing.assert_allclose(saved.embedding, embedding)
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


def test_check_in_repository_crud_filters_and_limit(session: Session) -> None:
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
    first_time = datetime(2026, 9, 21, 10, tzinfo=UTC)
    first = repository.add(
        CheckInRecord(
            id=None,
            user_id=user.id,
            matched_face_profile_id=profile.id,
            checkin_time=first_time,
            similarity_score=0.91,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )
    second = repository.add(
        CheckInRecord(
            id=None,
            user_id=None,
            matched_face_profile_id=None,
            checkin_time=first_time + timedelta(hours=1),
            similarity_score=0.2,
            threshold=0.4,
            status=CheckInStatus.UNMATCHED,
        )
    )

    assert repository.get(first.id) == first
    assert [record.id for record in repository.list()] == [second.id, first.id]
    assert [record.id for record in repository.list(user_id=user.id)] == [first.id]
    assert repository.list(start=first_time + timedelta(minutes=30), limit=1) == [second]
    assert repository.list(end=first_time + timedelta(minutes=30)) == [first]
    with pytest.raises(ValueError, match="positive"):
        repository.list(limit=0)

    repository.delete(second.id)
    assert repository.get(second.id) is None
