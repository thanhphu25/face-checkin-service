from datetime import UTC, datetime

import numpy as np

from app.domain.entities import CheckInRecord, CheckInStatus, FaceProfile, Role, User
from app.models import CheckInRecordORM, FaceProfileORM, UserORM


def _utc(value: datetime) -> datetime:
    """Restore UTC information that SQLite drops from timezone-aware columns."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def user_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        email=row.email,
        hashed_password=row.hashed_password,
        role=Role(row.role),
        full_name=row.full_name,
        created_at=_utc(row.created_at),
    )


def face_profile_to_domain(row: FaceProfileORM) -> FaceProfile:
    embedding = np.frombuffer(row.embedding, dtype="<f4")
    if embedding.size != row.embedding_dim:
        raise ValueError(
            f"Corrupt embedding for face profile {row.id}: "
            f"expected {row.embedding_dim} values, got {embedding.size}"
        )
    return FaceProfile(
        id=row.id,
        user_id=row.user_id,
        embedding=embedding.copy(),
        model_name=row.model_name,
        created_at=_utc(row.created_at),
    )


def check_in_to_domain(row: CheckInRecordORM) -> CheckInRecord:
    return CheckInRecord(
        id=row.id,
        user_id=row.user_id,
        matched_face_profile_id=row.matched_face_profile_id,
        checkin_time=_utc(row.checkin_time),
        similarity_score=row.similarity_score,
        threshold=row.threshold,
        status=CheckInStatus(row.status),
    )
