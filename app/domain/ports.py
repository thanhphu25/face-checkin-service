from abc import ABC, abstractmethod
from datetime import datetime

import numpy as np

from app.domain.entities import CheckInRecord, FaceProfile, User


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> User:
        """Persist a user and return it with its generated identifier."""

    @abstractmethod
    def get(self, user_id: int) -> User | None:
        """Return a user by identifier, or None when it does not exist."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Return a user by its normalized email address."""

    @abstractmethod
    def list_all(self) -> list[User]:
        """Return all users in stable identifier order."""

    @abstractmethod
    def delete(self, user_id: int) -> None:
        """Delete a user when it exists."""


class FaceProfileRepository(ABC):
    @abstractmethod
    def add(self, profile: FaceProfile) -> FaceProfile:
        """Persist a face profile and return it with its generated identifier."""

    @abstractmethod
    def get(self, profile_id: int) -> FaceProfile | None:
        """Return a face profile by identifier, or None when absent."""

    @abstractmethod
    def list_all(self) -> list[FaceProfile]:
        """Return all profiles used by the face-matching scan."""

    @abstractmethod
    def list_by_user(self, user_id: int) -> list[FaceProfile]:
        """Return every face profile registered by one user."""

    @abstractmethod
    def delete(self, profile_id: int) -> None:
        """Delete a face profile when it exists."""


class CheckInRepository(ABC):
    @abstractmethod
    def add(self, record: CheckInRecord) -> CheckInRecord:
        """Persist a check-in record and return it with its generated identifier."""

    @abstractmethod
    def get(self, record_id: int) -> CheckInRecord | None:
        """Return a check-in record by identifier, or None when absent."""

    @abstractmethod
    def list(
        self,
        *,
        user_id: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
    ) -> list[CheckInRecord]:
        """Return newest records matching the optional user and time filters."""

    @abstractmethod
    def delete(self, record_id: int) -> None:
        """Delete a check-in record when it exists."""


class FaceEmbedder(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the stable name of the model that produces embeddings."""

    @abstractmethod
    def embed(self, image_bytes: bytes) -> np.ndarray:
        """Return a float32, L2-normalized embedding for the supplied image."""
