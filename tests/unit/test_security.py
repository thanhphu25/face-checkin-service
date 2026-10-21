from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import (
    Argon2PasswordHasher,
    PBKDF2PasswordHasher,
    create_access_token,
    decode_access_token,
)
from app.domain import InvalidToken, Role

SECRET = "unit-test-secret-that-is-not-used-outside-tests"


def test_argon2id_hash_is_salted_and_verifiable_without_plaintext() -> None:
    hasher = Argon2PasswordHasher()

    first_hash = hasher.hash("strong-password")
    second_hash = hasher.hash("strong-password")

    assert first_hash.startswith("$argon2id$")
    assert "strong-password" not in first_hash
    assert first_hash != second_hash
    assert hasher.verify("strong-password", first_hash)
    assert not hasher.verify("wrong-password", first_hash)
    assert not hasher.verify("strong-password", "malformed-hash")


def test_argon2_hasher_verifies_legacy_week3_pbkdf2_hashes() -> None:
    legacy_hash = PBKDF2PasswordHasher().hash("legacy-password")

    assert Argon2PasswordHasher().verify("legacy-password", legacy_hash)
    assert not Argon2PasswordHasher().verify("wrong-password", legacy_hash)


def test_jwt_round_trip_contains_subject_role_and_expiration() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    token = create_access_token(
        user_id=42,
        role=Role.ADMIN,
        secret=SECRET,
        algorithm="HS256",
        expires_delta=timedelta(minutes=30),
        now=now,
    )

    claims = decode_access_token(token=token, secret=SECRET, algorithm="HS256")

    assert claims.user_id == 42
    assert claims.role is Role.ADMIN
    assert claims.issued_at == now
    assert claims.expires_at == now + timedelta(minutes=30)


@pytest.mark.parametrize("token", ["not-a-jwt", "", "a.b.c"])
def test_decode_rejects_malformed_jwt(token: str) -> None:
    with pytest.raises(InvalidToken):
        decode_access_token(token=token, secret=SECRET, algorithm="HS256")


def test_decode_rejects_wrong_signature_and_expired_token() -> None:
    valid_token = create_access_token(
        user_id=1,
        role=Role.USER,
        secret=SECRET,
        algorithm="HS256",
        expires_delta=timedelta(minutes=5),
    )
    expired_token = create_access_token(
        user_id=1,
        role=Role.USER,
        secret=SECRET,
        algorithm="HS256",
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(InvalidToken):
        decode_access_token(token=valid_token, secret="different-secret", algorithm="HS256")
    with pytest.raises(InvalidToken):
        decode_access_token(token=expired_token, secret=SECRET, algorithm="HS256")
