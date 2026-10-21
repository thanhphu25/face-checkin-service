import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from argon2 import PasswordHasher as Argon2Engine
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type

from app.domain.entities import Role
from app.domain.errors import InvalidToken
from app.domain.ports import PasswordHasher

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16


class PBKDF2PasswordHasher(PasswordHasher):
    """Legacy week-3 verifier retained for existing development data."""

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
        return "$".join(
            (
                _ALGORITHM,
                str(_ITERATIONS),
                base64.urlsafe_b64encode(salt).decode(),
                base64.urlsafe_b64encode(digest).decode(),
            )
        )

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
            if algorithm != _ALGORITHM:
                return False
            iterations = int(iterations_text)
            salt = base64.urlsafe_b64decode(salt_text.encode())
            expected = base64.urlsafe_b64decode(digest_text.encode())
        except (ValueError, TypeError):
            return False

        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(actual, expected)


@lru_cache
def _dummy_argon2_hash() -> str:
    return Argon2Engine(type=Type.ID).hash(secrets.token_urlsafe(32))


class Argon2PasswordHasher(PasswordHasher):
    """Argon2id adapter for new hashes with verification of legacy PBKDF2 hashes."""

    def __init__(self) -> None:
        self._argon2 = Argon2Engine(type=Type.ID)
        self._legacy = PBKDF2PasswordHasher()

    def hash(self, password: str) -> str:
        return self._argon2.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        if password_hash.startswith(f"{_ALGORITHM}$"):
            return self._legacy.verify(password, password_hash)

        candidate_hash = password_hash
        is_dummy = not password_hash.startswith("$argon2")
        if is_dummy:
            candidate_hash = _dummy_argon2_hash()
        try:
            verified = self._argon2.verify(candidate_hash, password)
        except (InvalidHashError, VerificationError):
            return False
        return verified and not is_dummy


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int
    role: Role
    issued_at: datetime
    expires_at: datetime


def create_access_token(
    *,
    user_id: int | None,
    role: Role,
    secret: str,
    algorithm: str,
    expires_delta: timedelta,
    now: datetime | None = None,
) -> str:
    if user_id is None or user_id < 1:
        raise ValueError("JWT subject must be a persisted user identifier")
    issued_at = now or datetime.now(UTC)
    if issued_at.tzinfo is None:
        raise ValueError("JWT timestamps must be timezone-aware")
    expires_at = issued_at + expires_delta
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role.value,
            "iat": issued_at,
            "exp": expires_at,
        },
        secret,
        algorithm=algorithm,
    )


def decode_access_token(*, token: str, secret: str, algorithm: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
        user_id = int(payload["sub"])
        role = Role(payload["role"])
        issued_at = datetime.fromtimestamp(payload["iat"], UTC)
        expires_at = datetime.fromtimestamp(payload["exp"], UTC)
        if user_id < 1 or expires_at <= issued_at:
            raise ValueError
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidToken() from exc
    return AccessTokenClaims(
        user_id=user_id,
        role=role,
        issued_at=issued_at,
        expires_at=expires_at,
    )
