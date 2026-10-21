from datetime import UTC, datetime

import numpy as np
import pytest
from pydantic import ValidationError

from app.domain import CheckInRecord, CheckInStatus, FaceProfile, User
from app.schemas import (
    CheckInRead,
    FaceProfileRead,
    TokenResponse,
    UserCreate,
    UserRead,
)


def test_user_schemas_validate_input_without_exposing_password_hash() -> None:
    request = UserCreate(
        email="  user@example.com  ",
        password="strong-password",
        full_name="  Example User  ",
    )
    domain_user = User(
        id=1,
        email=request.email,
        hashed_password="should-never-leak",
        role=request.role,
        full_name=request.full_name,
        created_at=datetime.now(UTC),
    )

    response = UserRead.model_validate(domain_user)

    assert request.email == "user@example.com"
    assert request.full_name == "Example User"
    assert request.password.get_secret_value() == "strong-password"
    assert "password" not in response.model_dump()
    assert "hashed_password" not in response.model_dump()
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="short", full_name="User")


def test_auth_schema_returns_bearer_token() -> None:
    response = TokenResponse(access_token="encoded-jwt")

    assert response.model_dump() == {"access_token": "encoded-jwt", "token_type": "bearer"}


def test_face_profile_schemas_keep_embedding_out_of_response() -> None:
    profile = FaceProfile(
        id=1,
        user_id=2,
        embedding=np.array([0.6, 0.8], dtype=np.float32),
        model_name="buffalo_s",
        created_at=datetime.now(UTC),
    )

    response = FaceProfileRead.model_validate(profile)

    assert "embedding" not in response.model_dump()


def test_check_in_schema_validates_result() -> None:
    now = datetime.now(UTC)
    record = CheckInRecord(
        id=1,
        user_id=2,
        matched_face_profile_id=3,
        checkin_time=now,
        similarity_score=0.91,
        threshold=0.4,
        status=CheckInStatus.SUCCESS,
    )

    response = CheckInRead.model_validate(record)
    assert response.status is CheckInStatus.SUCCESS
