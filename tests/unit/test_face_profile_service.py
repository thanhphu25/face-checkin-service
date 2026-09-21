from datetime import UTC, datetime

import numpy as np
import pytest

from app.domain import (
    FaceEmbedder,
    FaceEmbeddingFailed,
    FaceProfile,
    FaceProfileNotFound,
    FaceProfileRepository,
    Role,
    User,
    UserNotFound,
    UserRepository,
)
from app.services import FaceProfileService


class UserStore(UserRepository):
    def __init__(self, users: list[User]) -> None:
        self.items = {user.id: user for user in users}

    def add(self, user: User) -> User:
        self.items[user.id] = user
        return user

    def get(self, user_id: int) -> User | None:
        return self.items.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.items.values() if user.email == email), None)

    def list_all(self) -> list[User]:
        return list(self.items.values())

    def delete(self, user_id: int) -> None:
        self.items.pop(user_id, None)


class ProfileStore(FaceProfileRepository):
    def __init__(self) -> None:
        self.items: dict[int, FaceProfile] = {}

    def add(self, profile: FaceProfile) -> FaceProfile:
        saved = FaceProfile(
            id=max(self.items, default=0) + 1,
            user_id=profile.user_id,
            embedding=profile.embedding,
            model_name=profile.model_name,
            created_at=profile.created_at,
        )
        self.items[saved.id] = saved
        return saved

    def get(self, profile_id: int) -> FaceProfile | None:
        return self.items.get(profile_id)

    def list_all(self) -> list[FaceProfile]:
        return list(self.items.values())

    def list_by_user(self, user_id: int) -> list[FaceProfile]:
        return [profile for profile in self.items.values() if profile.user_id == user_id]

    def delete(self, profile_id: int) -> None:
        self.items.pop(profile_id, None)


class FixedEmbedder(FaceEmbedder):
    def __init__(self, embedding: np.ndarray) -> None:
        self.embedding = embedding
        self.images: list[bytes] = []

    @property
    def model_name(self) -> str:
        return "buffalo_s"

    def embed(self, image_bytes: bytes) -> np.ndarray:
        self.images.append(image_bytes)
        return self.embedding


def _user(user_id: int = 1) -> User:
    return User(
        id=user_id,
        email="person@example.com",
        hashed_password="hashed",
        role=Role.USER,
        full_name="Person",
        created_at=datetime(2026, 9, 21, 8, tzinfo=UTC),
    )


def _service(
    embedding: np.ndarray | None = None,
) -> tuple[FaceProfileService, UserStore, ProfileStore, FixedEmbedder]:
    users = UserStore([_user()])
    profiles = ProfileStore()
    embedder = FixedEmbedder(np.array([3.0, 4.0]) if embedding is None else embedding)
    service = FaceProfileService(
        profiles,
        users,
        embedder,
        clock=lambda: datetime(2026, 9, 21, 9, tzinfo=UTC),
    )
    return service, users, profiles, embedder


def test_register_face_uses_embedder_and_persists_normalized_float32() -> None:
    service, _, profiles, embedder = _service()

    profile = service.register_face(1, b"image")

    assert profile.id == 1
    assert profile.model_name == "buffalo_s"
    assert profile.embedding.dtype == np.float32
    np.testing.assert_allclose(profile.embedding, np.array([0.6, 0.8], dtype=np.float32))
    assert profiles.items[profile.id] is profile
    assert embedder.images == [b"image"]


def test_register_face_requires_existing_user_and_valid_embedding() -> None:
    service, _, _, _ = _service()
    with pytest.raises(UserNotFound):
        service.register_face(404, b"image")

    invalid_service, _, _, _ = _service(np.zeros(2))
    with pytest.raises(FaceEmbeddingFailed):
        invalid_service.register_face(1, b"image")


def test_list_profiles_all_or_by_existing_user() -> None:
    service, _, _, _ = _service()
    profile = service.register_face(1, b"image")

    assert service.list_profiles() == [profile]
    assert service.list_profiles(user_id=1) == [profile]
    with pytest.raises(UserNotFound):
        service.list_profiles(user_id=404)


def test_delete_profile_requires_existing_profile() -> None:
    service, _, _, _ = _service()
    profile = service.register_face(1, b"image")

    service.delete_profile(profile.id)
    assert service.list_profiles() == []
    with pytest.raises(FaceProfileNotFound):
        service.delete_profile(profile.id)
