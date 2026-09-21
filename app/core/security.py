import base64
import hashlib
import hmac
import secrets

from app.domain.ports import PasswordHasher

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16


class PBKDF2PasswordHasher(PasswordHasher):
    """Small stdlib adapter used until the authentication work in week 4."""

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
