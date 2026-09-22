import asyncio
from datetime import timedelta

import numpy as np
from alembic.config import Config

from alembic import command
from app.api.deps import (
    get_embedder,
    get_engine,
    get_password_hasher,
    get_session_factory,
)
from app.core.config import get_settings
from app.core.security import create_access_token
from app.domain import FaceEmbedder, Role
from app.main import create_app
from app.repositories import SQLAlchemyUserRepository
from app.services import UserService

SECRET = "sqlite-integration-secret-that-is-only-used-by-tests"
ADMIN_PASSWORD = "admin-integration-password"
USER_PASSWORD = "user-integration-password"
OTHER_PASSWORD = "other-integration-password"


class DeterministicEmbedder(FaceEmbedder):
    @property
    def model_name(self) -> str:
        return "test-model"

    def embed(self, image_bytes: bytes) -> np.ndarray:
        vectors = {
            b"user-face": np.array([1.0, 0.0], dtype=np.float32),
            b"other-face": np.array([0.0, 1.0], dtype=np.float32),
        }
        return vectors[image_bytes]


def _reset_dependencies() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_embedder.cache_clear()
    get_password_hasher.cache_clear()
    get_settings.cache_clear()


def test_sqlite_login_shared_auth_and_rbac_end_to_end(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{(tmp_path / 'week4-auth.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("EMBEDDING_MODEL", "test-model")
    _reset_dependencies()
    command.upgrade(Config("alembic.ini"), "head")

    with get_session_factory()() as session:
        UserService(
            SQLAlchemyUserRepository(session),
            get_password_hasher(),
        ).create_user(
            email="admin@example.com",
            password=ADMIN_PASSWORD,
            full_name="Admin",
            role=Role.ADMIN,
        )
        session.commit()

    app = create_app()
    app.dependency_overrides[get_embedder] = DeterministicEmbedder

    async def exercise_api() -> dict[str, object]:
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:

            async def login(email: str, password: str):
                return await client.post(
                    "/api/v1/auth/login",
                    data={"username": email, "password": password},
                )

            admin_login = await login(" ADMIN@EXAMPLE.COM ", ADMIN_PASSWORD)
            wrong_password = await login("admin@example.com", "wrong-password")
            missing_email = await login("missing@example.com", "wrong-password")
            admin_token = admin_login.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            user_response = await client.post(
                "/api/v1/users",
                headers=admin_headers,
                json={
                    "email": "user@example.com",
                    "password": USER_PASSWORD,
                    "full_name": "User",
                },
            )
            other_response = await client.post(
                "/api/v1/users",
                headers=admin_headers,
                json={
                    "email": "other@example.com",
                    "password": OTHER_PASSWORD,
                    "full_name": "Other",
                },
            )
            user_id = user_response.json()["id"]
            other_id = other_response.json()["id"]

            user_login = await login(" USER@EXAMPLE.COM ", USER_PASSWORD)
            other_login = await login("other@example.com", OTHER_PASSWORD)
            user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}
            other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

            me = await client.get("/api/v1/auth/me", headers=user_headers)
            missing_token = await client.get("/api/v1/auth/me")
            broken_token = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer broken.token.value"},
            )
            expired_token = create_access_token(
                user_id=user_id,
                role=Role.USER,
                secret=SECRET,
                algorithm="HS256",
                expires_delta=timedelta(minutes=-1),
            )
            expired = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
            protected_post_missing_token = await client.post(
                "/api/v1/face-profiles",
                files={"image": ("user.png", b"user-face", "image/png")},
            )
            protected_get_missing_token = await client.get("/api/v1/checkins")

            user_create_forbidden = await client.post(
                "/api/v1/users",
                headers=user_headers,
                json={
                    "email": "blocked@example.com",
                    "password": "blocked-password",
                    "full_name": "Blocked",
                },
            )
            self_read = await client.get(f"/api/v1/users/{user_id}", headers=user_headers)
            other_read_forbidden = await client.get(
                f"/api/v1/users/{other_id}", headers=user_headers
            )
            admin_read = await client.get(f"/api/v1/users/{other_id}", headers=admin_headers)
            missing_resource = await client.get("/api/v1/users/999999", headers=user_headers)

            user_profile = await client.post(
                "/api/v1/face-profiles",
                headers=user_headers,
                data={"user_id": str(other_id)},
                files={"image": ("user.png", b"user-face", "image/png")},
            )
            other_profile = await client.post(
                "/api/v1/face-profiles",
                headers=other_headers,
                files={"image": ("other.png", b"other-face", "image/png")},
            )
            user_profile_id = user_profile.json()["id"]
            other_profile_id = other_profile.json()["id"]
            delete_other_profile_forbidden = await client.delete(
                f"/api/v1/face-profiles/{other_profile_id}", headers=user_headers
            )
            user_profiles = await client.get(
                f"/api/v1/face-profiles?user_id={other_id}", headers=user_headers
            )
            admin_profiles = await client.get("/api/v1/face-profiles", headers=admin_headers)

            user_check_in = await client.post(
                "/api/v1/checkins",
                files={"image": ("user.png", b"user-face", "image/png")},
            )
            other_check_in = await client.post(
                "/api/v1/checkins",
                files={"image": ("other.png", b"other-face", "image/png")},
            )
            user_record_id = user_check_in.json()["id"]
            other_record_id = other_check_in.json()["id"]

            user_history = await client.get(
                f"/api/v1/checkins?user_id={other_id}", headers=user_headers
            )
            admin_history = await client.get("/api/v1/checkins", headers=admin_headers)
            admin_filtered_history = await client.get(
                f"/api/v1/checkins?user_id={other_id}", headers=admin_headers
            )
            other_record_forbidden = await client.get(
                f"/api/v1/checkins/{other_record_id}", headers=user_headers
            )
            user_delete_check_in_forbidden = await client.delete(
                f"/api/v1/checkins/{user_record_id}", headers=user_headers
            )
            admin_delete_check_in = await client.delete(
                f"/api/v1/checkins/{other_record_id}", headers=admin_headers
            )
            admin_delete_profile = await client.delete(
                f"/api/v1/face-profiles/{other_profile_id}", headers=admin_headers
            )

            return {
                "admin_login": admin_login,
                "wrong_password": wrong_password,
                "missing_email": missing_email,
                "user_response": user_response,
                "other_response": other_response,
                "me": me,
                "missing_token": missing_token,
                "broken_token": broken_token,
                "expired": expired,
                "protected_post_missing_token": protected_post_missing_token,
                "protected_get_missing_token": protected_get_missing_token,
                "user_create_forbidden": user_create_forbidden,
                "self_read": self_read,
                "other_read_forbidden": other_read_forbidden,
                "admin_read": admin_read,
                "missing_resource": missing_resource,
                "user_profile": user_profile,
                "user_profile_id": user_profile_id,
                "delete_other_profile_forbidden": delete_other_profile_forbidden,
                "user_profiles": user_profiles,
                "admin_profiles": admin_profiles,
                "user_check_in": user_check_in,
                "other_check_in": other_check_in,
                "user_history": user_history,
                "admin_history": admin_history,
                "admin_filtered_history": admin_filtered_history,
                "other_record_forbidden": other_record_forbidden,
                "user_delete_check_in_forbidden": user_delete_check_in_forbidden,
                "admin_delete_check_in": admin_delete_check_in,
                "admin_delete_profile": admin_delete_profile,
                "user_id": user_id,
                "other_id": other_id,
            }

    result = asyncio.run(exercise_api())

    assert result["admin_login"].status_code == 200
    assert result["wrong_password"].status_code == result["missing_email"].status_code == 401
    assert result["wrong_password"].json() == result["missing_email"].json()
    assert result["user_response"].status_code == result["other_response"].status_code == 201
    assert result["me"].status_code == 200
    assert result["me"].json()["id"] == result["user_id"]
    assert "hashed_password" not in result["me"].json()
    assert [
        result["missing_token"].status_code,
        result["broken_token"].status_code,
        result["expired"].status_code,
        result["protected_post_missing_token"].status_code,
        result["protected_get_missing_token"].status_code,
    ] == [401, 401, 401, 401, 401]
    assert result["user_create_forbidden"].status_code == 403
    assert result["self_read"].status_code == 200
    assert result["other_read_forbidden"].status_code == 403
    assert result["admin_read"].status_code == 200
    assert result["missing_resource"].status_code == 404
    assert result["user_profile"].status_code == 201
    assert result["user_profile"].json()["user_id"] == result["user_id"]
    assert "embedding" not in result["user_profile"].json()
    assert result["delete_other_profile_forbidden"].status_code == 403
    assert {item["user_id"] for item in result["user_profiles"].json()} == {result["user_id"]}
    assert {item["user_id"] for item in result["admin_profiles"].json()} == {
        result["user_id"],
        result["other_id"],
    }
    assert result["user_check_in"].status_code == result["other_check_in"].status_code == 201
    assert result["user_history"].status_code == 200
    assert {item["user_id"] for item in result["user_history"].json()} == {result["user_id"]}
    assert {item["user_id"] for item in result["admin_history"].json()} == {
        result["user_id"],
        result["other_id"],
    }
    assert {item["user_id"] for item in result["admin_filtered_history"].json()} == {
        result["other_id"]
    }
    assert result["other_record_forbidden"].status_code == 403
    assert result["user_delete_check_in_forbidden"].status_code == 403
    assert result["admin_delete_check_in"].status_code == 204
    assert result["admin_delete_profile"].status_code == 204

    with get_session_factory()() as session:
        persisted_users = SQLAlchemyUserRepository(session).list_all()
    assert len(persisted_users) == 3
    assert all(user.hashed_password.startswith("$argon2id$") for user in persisted_users)
    assert all(
        password not in user.hashed_password
        for user in persisted_users
        for password in (ADMIN_PASSWORD, USER_PASSWORD, OTHER_PASSWORD)
    )

    app.dependency_overrides.clear()
    _reset_dependencies()
