from datetime import UTC, datetime

import numpy as np
import pytest

from app.domain import (
    CheckInRecord,
    CheckInRepository,
    CheckInStatus,
    FaceProfile,
    FaceProfileRepository,
    Role,
    User,
    UserRepository,
)


def test_domain_entities_keep_framework_free_values() -> None:
    created_at = datetime.now(UTC)
    embedding = np.array([0.6, 0.8], dtype=np.float32)

    user = User(
        id=None,
        email="user@example.com",
        hashed_password="hashed",
        role=Role.USER,
        full_name="Example User",
        created_at=created_at,
    )
    profile = FaceProfile(
        id=None,
        user_id=1,
        embedding=embedding,
        model_name="buffalo_s",
        created_at=created_at,
    )
    record = CheckInRecord(
        id=None,
        user_id=1,
        matched_face_profile_id=1,
        checkin_time=created_at,
        similarity_score=0.91,
        threshold=0.4,
        status=CheckInStatus.SUCCESS,
    )

    assert user.role == "user"
    assert profile.embedding is embedding
    assert record.status == "success"


@pytest.mark.parametrize(
    "repository_type",
    [UserRepository, FaceProfileRepository, CheckInRepository],
)
def test_repository_ports_are_abstract(repository_type: type) -> None:
    with pytest.raises(TypeError):
        repository_type()
