import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import FaceProfile
from app.domain.ports import FaceProfileRepository
from app.models import FaceProfileORM
from app.repositories.mappers import face_profile_to_domain


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
        return face_profile_to_domain(row)

    def get(self, profile_id: int) -> FaceProfile | None:
        row = self._session.get(FaceProfileORM, profile_id)
        return face_profile_to_domain(row) if row is not None else None

    def list_all(self) -> list[FaceProfile]:
        rows = self._session.scalars(select(FaceProfileORM).order_by(FaceProfileORM.id)).all()
        return [face_profile_to_domain(row) for row in rows]

    def list_by_user(self, user_id: int) -> list[FaceProfile]:
        statement = (
            select(FaceProfileORM)
            .where(FaceProfileORM.user_id == user_id)
            .order_by(FaceProfileORM.id)
        )
        return [face_profile_to_domain(row) for row in self._session.scalars(statement).all()]

    def delete(self, profile_id: int) -> None:
        row = self._session.get(FaceProfileORM, profile_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
