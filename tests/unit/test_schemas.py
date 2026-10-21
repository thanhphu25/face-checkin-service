from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from pydantic import ValidationError

from app.domain import CheckInRecord, CheckInStatus, FaceProfile, User
from app.schemas import (
    CheckInCreate,
    CheckInListQuery,
    CheckInRead,
    FaceProfileCreate,
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
    request = FaceProfileCreate(image_bytes=b"image")
    profile = FaceProfile(
        id=1,
        user_id=2,
        embedding=np.array([0.6, 0.8], dtype=np.float32),
        model_name="buffalo_s",
        created_at=datetime.now(UTC),
    )

    response = FaceProfileRead.model_validate(profile)

    assert request.image_bytes == b"image"
    assert "embedding" not in response.model_dump()
    with pytest.raises(ValidationError):
        FaceProfileCreate(image_bytes=b"")


def test_check_in_schemas_validate_result_and_query_range() -> None:
    now = datetime.now(UTC)
    request = CheckInCreate(image_bytes=b"image")
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
    query = CheckInListQuery(user_id=2, start=now, end=now + timedelta(hours=1))

    assert request.image_bytes == b"image"
    assert response.status is CheckInStatus.SUCCESS
    assert query.limit == 50
    with pytest.raises(ValidationError, match="end must be later"):
        CheckInListQuery(start=now, end=now)
