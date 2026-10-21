from collections.abc import Callable
from datetime import UTC, datetime

import numpy as np

from app.domain.entities import FaceProfile, User
from app.domain.errors import FaceEmbeddingFailed, FaceProfileNotFound, UserNotFound
from app.domain.ports import FaceEmbedder, FaceProfileRepository, UserRepository
from app.services.authorization import require_owner_or_admin, scope_user_id


class FaceProfileService:
    def __init__(
        self,
        profiles: FaceProfileRepository,
        users: UserRepository,
        embedder: FaceEmbedder,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profiles = profiles
        self._users = users
        self._embedder = embedder
        self._clock = clock or (lambda: datetime.now(UTC))

    def register_face(self, user_id: int, image_bytes: bytes) -> FaceProfile:
        if self._users.get(user_id) is None:
            raise UserNotFound(f"User {user_id} was not found")

        embedding = np.asarray(self._embedder.embed(image_bytes), dtype=np.float32)
        if embedding.ndim != 1 or embedding.size == 0 or not np.all(np.isfinite(embedding)):
            raise FaceEmbeddingFailed("Face embedder returned an invalid embedding")
        norm = float(np.linalg.norm(embedding))
        if not np.isfinite(norm) or norm <= np.finfo(np.float32).eps:
            raise FaceEmbeddingFailed("Face embedder returned a zero-length embedding")

        return self._profiles.add(
            FaceProfile(
                id=None,
                user_id=user_id,
                embedding=np.ascontiguousarray(embedding / norm, dtype=np.float32),
                model_name=self._embedder.model_name,
                created_at=self._clock(),
            )
        )

    def register_face_for(self, requester: User, image_bytes: bytes) -> FaceProfile:
        if requester.id is None:
            raise UserNotFound("Authenticated user is not persisted")
        return self.register_face(requester.id, image_bytes)

    def list_profiles(self, *, user_id: int | None = None) -> list[FaceProfile]:
        if user_id is None:
            return self._profiles.list_all()
        if self._users.get(user_id) is None:
            raise UserNotFound(f"User {user_id} was not found")
        return self._profiles.list_by_user(user_id)

    def list_profiles_for(
        self, requester: User, *, user_id: int | None = None
    ) -> list[FaceProfile]:
        scoped_user_id = scope_user_id(requester, requested_user_id=user_id)
        return self.list_profiles(user_id=scoped_user_id)

    def delete_profile(self, profile_id: int) -> None:
        if self._profiles.get(profile_id) is None:
            raise FaceProfileNotFound(f"Face profile {profile_id} was not found")
        self._profiles.delete(profile_id)

    def delete_profile_for(self, requester: User, profile_id: int) -> None:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise FaceProfileNotFound(f"Face profile {profile_id} was not found")
        require_owner_or_admin(requester, owner_id=profile.user_id)
        self._profiles.delete(profile_id)
