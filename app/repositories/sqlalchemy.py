from datetime import UTC, datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import CheckInRecord, CheckInStatus, FaceProfile, Role, User
from app.domain.ports import CheckInRepository, FaceProfileRepository, UserRepository
from app.models import CheckInRecordORM, FaceProfileORM, UserORM


def _utc(value: datetime) -> datetime:
    """Restore UTC information that SQLite drops from timezone-aware columns."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _user_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        email=row.email,
        hashed_password=row.hashed_password,
        role=Role(row.role),
        full_name=row.full_name,
        created_at=_utc(row.created_at),
    )


def _profile_to_domain(row: FaceProfileORM) -> FaceProfile:
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


def _record_to_domain(row: CheckInRecordORM) -> CheckInRecord:
    return CheckInRecord(
        id=row.id,
        user_id=row.user_id,
        matched_face_profile_id=row.matched_face_profile_id,
        checkin_time=_utc(row.checkin_time),
        similarity_score=row.similarity_score,
        threshold=row.threshold,
        status=CheckInStatus(row.status),
    )


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        row = UserORM(
            email=user.email,
            hashed_password=user.hashed_password,
            role=user.role.value,
            full_name=user.full_name,
            created_at=user.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return _user_to_domain(row)

    def get(self, user_id: int) -> User | None:
        row = self._session.get(UserORM, user_id)
        return _user_to_domain(row) if row is not None else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalar(select(UserORM).where(UserORM.email == email))
        return _user_to_domain(row) if row is not None else None

    def list_all(self) -> list[User]:
        rows = self._session.scalars(select(UserORM).order_by(UserORM.id)).all()
        return [_user_to_domain(row) for row in rows]

    def delete(self, user_id: int) -> None:
        row = self._session.get(UserORM, user_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()


class SQLAlchemyFaceProfileRepository(FaceProfileRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, profile: FaceProfile) -> FaceProfile:
        embedding = np.asarray(profile.embedding, dtype="<f4")
        if embedding.ndim != 1 or embedding.size == 0:
            raise ValueError("Face profile embedding must be a non-empty one-dimensional vector")
        row = FaceProfileORM(
            user_id=profile.user_id,
            embedding=np.ascontiguousarray(embedding).tobytes(),
            embedding_dim=embedding.size,
            model_name=profile.model_name,
            created_at=profile.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return _profile_to_domain(row)

    def get(self, profile_id: int) -> FaceProfile | None:
        row = self._session.get(FaceProfileORM, profile_id)
        return _profile_to_domain(row) if row is not None else None

    def list_all(self) -> list[FaceProfile]:
        rows = self._session.scalars(select(FaceProfileORM).order_by(FaceProfileORM.id)).all()
        return [_profile_to_domain(row) for row in rows]

    def list_by_user(self, user_id: int) -> list[FaceProfile]:
        statement = (
            select(FaceProfileORM)
            .where(FaceProfileORM.user_id == user_id)
            .order_by(FaceProfileORM.id)
        )
        return [_profile_to_domain(row) for row in self._session.scalars(statement).all()]

    def delete(self, profile_id: int) -> None:
        row = self._session.get(FaceProfileORM, profile_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()


class SQLAlchemyCheckInRepository(CheckInRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: CheckInRecord) -> CheckInRecord:
        row = CheckInRecordORM(
            user_id=record.user_id,
            matched_face_profile_id=record.matched_face_profile_id,
            checkin_time=record.checkin_time,
            similarity_score=record.similarity_score,
            threshold=record.threshold,
            status=record.status.value,
        )
        self._session.add(row)
        self._session.flush()
        return _record_to_domain(row)

    def get(self, record_id: int) -> CheckInRecord | None:
        row = self._session.get(CheckInRecordORM, record_id)
        return _record_to_domain(row) if row is not None else None

    def list(
        self,
        *,
        user_id: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
    ) -> list[CheckInRecord]:
        if limit < 1:
            raise ValueError("Check-in list limit must be positive")
        statement = select(CheckInRecordORM)
        if user_id is not None:
            statement = statement.where(CheckInRecordORM.user_id == user_id)
        if start is not None:
            statement = statement.where(CheckInRecordORM.checkin_time >= start)
        if end is not None:
            statement = statement.where(CheckInRecordORM.checkin_time < end)
        statement = statement.order_by(
            CheckInRecordORM.checkin_time.desc(), CheckInRecordORM.id.desc()
        ).limit(limit)
        return [_record_to_domain(row) for row in self._session.scalars(statement).all()]

    def delete(self, record_id: int) -> None:
        row = self._session.get(CheckInRecordORM, record_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
