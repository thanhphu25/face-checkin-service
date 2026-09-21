from datetime import UTC, datetime

import pytest

from app.domain import (
    EmailAlreadyExists,
    InvalidEmail,
    PasswordHasher,
    Role,
    User,
    UserNotFound,
    UserRepository,
)
from app.services import UserService


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.items: dict[int, User] = {}

    def add(self, user: User) -> User:
        saved = User(
            id=max(self.items, default=0) + 1,
            email=user.email,
            hashed_password=user.hashed_password,
            role=user.role,
            full_name=user.full_name,
            created_at=user.created_at,
        )
        self.items[saved.id] = saved
        return saved

    def get(self, user_id: int) -> User | None:
        return self.items.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.items.values() if user.email == email), None)

    def list_all(self) -> list[User]:
        return list(self.items.values())

    def delete(self, user_id: int) -> None:
        self.items.pop(user_id, None)


class RecordingPasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self.passwords: list[str] = []

    def hash(self, password: str) -> str:
        self.passwords.append(password)
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


def _service() -> tuple[UserService, InMemoryUserRepository, RecordingPasswordHasher]:
    repository = InMemoryUserRepository()
    hasher = RecordingPasswordHasher()
    service = UserService(
        repository,
        hasher,
        clock=lambda: datetime(2026, 9, 21, 8, tzinfo=UTC),
    )
    return service, repository, hasher


def test_create_user_normalizes_email_and_hashes_password() -> None:
    service, repository, hasher = _service()

    user = service.create_user(
        email="  Person@Example.COM ",
        password="strong-password",
        full_name=" Example Person ",
    )

    assert user.email == "person@example.com"
    assert user.hashed_password == "hashed:strong-password"
    assert user.role is Role.USER
    assert user.full_name == "Example Person"
    assert repository.items[user.id] == user
    assert hasher.passwords == ["strong-password"]


def test_create_user_rejects_duplicate_normalized_email() -> None:
    service, _, _ = _service()
    service.create_user(email="person@example.com", password="password", full_name="Person")

    with pytest.raises(EmailAlreadyExists):
        service.create_user(email=" PERSON@example.com ", password="password", full_name="Other")


@pytest.mark.parametrize("email", ["", "missing-at.example.com", "@example.com", "a@@b.com"])
def test_create_user_rejects_invalid_email(email: str) -> None:
    service, _, _ = _service()

    with pytest.raises(InvalidEmail):
        service.create_user(email=email, password="password", full_name="Person")


def test_get_list_and_delete_user_through_repository_port() -> None:
    service, _, _ = _service()
    user = service.create_user(email="person@example.com", password="password", full_name="Person")

    assert service.get_user(user.id) == user
    assert service.list_users() == [user]

    service.delete_user(user.id)
    assert service.list_users() == []
    with pytest.raises(UserNotFound):
        service.get_user(user.id)
    with pytest.raises(UserNotFound):
        service.delete_user(user.id)
