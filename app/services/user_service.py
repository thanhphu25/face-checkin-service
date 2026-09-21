from collections.abc import Callable
from datetime import UTC, datetime

from app.domain.entities import Role, User
from app.domain.errors import AuthenticationFailed, EmailAlreadyExists, InvalidEmail, UserNotFound
from app.domain.ports import PasswordHasher, UserRepository


class UserService:
    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasher,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role: Role = Role.USER,
    ) -> User:
        normalized_email = self.normalize_email(email)
        if self._users.get_by_email(normalized_email) is not None:
            raise EmailAlreadyExists(f"Email is already registered: {normalized_email}")

        return self._users.add(
            User(
                id=None,
                email=normalized_email,
                hashed_password=self._password_hasher.hash(password),
                role=role,
                full_name=full_name.strip(),
                created_at=self._clock(),
            )
        )

    def get_user(self, user_id: int) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise UserNotFound(f"User {user_id} was not found")
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        try:
            normalized_email = self.normalize_email(email)
        except InvalidEmail:
            normalized_email = ""
        user = self._users.get_by_email(normalized_email)
        password_hash = user.hashed_password if user is not None else ""
        password_matches = self._password_hasher.verify(password, password_hash)
        if user is None or not password_matches:
            raise AuthenticationFailed()
        return user

    def list_users(self) -> list[User]:
        return self._users.list_all()

    def delete_user(self, user_id: int) -> None:
        self.get_user(user_id)
        self._users.delete(user_id)

    @staticmethod
    def normalize_email(email: str) -> str:
        normalized = email.strip().casefold()
        local, separator, domain = normalized.partition("@")
        if not separator or not local or not domain or "@" in domain:
            raise InvalidEmail("Email address is invalid")
        return normalized
