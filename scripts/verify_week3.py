"""Run the week-3 API and real InsightFace flow against an isolated database."""

import argparse
import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import cv2
import insightface
import numpy as np
from alembic.config import Config

from alembic import command


def _real_face_image() -> bytes:
    source = Path(insightface.__file__).parent / "data" / "images" / "t1.jpg"
    image = cv2.imread(str(source))
    if image is None:
        raise RuntimeError(f"Cannot read InsightFace sample image: {source}")
    # Crop one face from the public group image bundled with the InsightFace wheel.
    crop = image[290:530, 690:900]
    encoded, payload = cv2.imencode(".jpg", crop)
    if not encoded:
        raise RuntimeError("Cannot encode the verification face crop")
    return payload.tobytes()


def _no_face_image() -> bytes:
    encoded, payload = cv2.imencode(".png", np.zeros((128, 128, 3), dtype=np.uint8))
    if not encoded:
        raise RuntimeError("Cannot encode the no-face verification image")
    return payload.tobytes()


def _reset_dependencies() -> None:
    from app.api.deps import (
        get_embedder,
        get_engine,
        get_password_hasher,
        get_session_factory,
    )
    from app.core.config import get_settings

    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_embedder.cache_clear()
    get_password_hasher.cache_clear()
    get_settings.cache_clear()


async def _exercise_api(database_url: str) -> dict[str, object]:
    from httpx2 import ASGITransport, AsyncClient

    from app.api.deps import get_embedder, get_password_hasher, get_session_factory
    from app.domain import Role
    from app.main import create_app
    from app.ml import InsightFaceEmbedder
    from app.repositories import (
        SQLAlchemyCheckInRepository,
        SQLAlchemyFaceProfileRepository,
        SQLAlchemyUserRepository,
    )
    from app.services import UserService

    embedder = InsightFaceEmbedder(model_name="buffalo_s")
    admin_email = f"week4-admin-{uuid4().hex}@example.com"
    admin_password = "week4-admin-verification-only"
    user_password = "week4-user-verification-only"
    with get_session_factory()() as session:
        admin = UserService(
            SQLAlchemyUserRepository(session),
            get_password_hasher(),
        ).create_user(
            email=admin_email,
            password=admin_password,
            full_name="Week 4 Verification Admin",
            role=Role.ADMIN,
        )
        session.commit()
    admin_id = admin.id

    app = create_app()
    app.dependency_overrides[get_embedder] = lambda: embedder
    transport = ASGITransport(app=app)
    email = f"week4-user-{uuid4().hex}@example.com"
    face_bytes = _real_face_image()

    user_id: int | None = None
    profile_id: int | None = None
    check_in_ids: list[int] = []
    admin_headers: dict[str, str] = {}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            admin_login = await client.post(
                "/api/v1/auth/login",
                data={"username": admin_email, "password": admin_password},
            )
            admin_login.raise_for_status()
            admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
            user_response = await client.post(
                "/api/v1/users",
                headers=admin_headers,
                json={
                    "email": email,
                    "password": user_password,
                    "full_name": "Week 4 Verification User",
                },
            )
            user_response.raise_for_status()
            user_body = user_response.json()
            user_id = user_body["id"]
            if "hashed_password" in user_body:
                raise AssertionError("Password hash leaked from the API")

            user_login = await client.post(
                "/api/v1/auth/login",
                data={"username": email.upper(), "password": user_password},
            )
            user_login.raise_for_status()
            user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}
            me_response = await client.get("/api/v1/auth/me", headers=user_headers)
            me_response.raise_for_status()
            forbidden_response = await client.post(
                "/api/v1/users",
                headers=user_headers,
                json={
                    "email": f"blocked-{uuid4().hex}@example.com",
                    "password": "blocked-verification-only",
                    "full_name": "Blocked Verification User",
                },
            )
            if forbidden_response.status_code != 403:
                raise AssertionError(f"Expected user create=403, got {forbidden_response.text}")
            invalid_token_response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer broken.token.value"},
            )
            if invalid_token_response.status_code != 401:
                raise AssertionError(
                    f"Expected invalid token=401, got {invalid_token_response.text}"
                )

            no_face_response = await client.post(
                "/api/v1/checkins",
                files={"image": ("blank.png", _no_face_image(), "image/png")},
            )
            if no_face_response.status_code != 422:
                raise AssertionError(f"Expected no_face=422, got {no_face_response.text}")
            no_face_body = no_face_response.json()
            check_in_ids.append(no_face_body["record_id"])

            profile_response = await client.post(
                "/api/v1/face-profiles",
                headers=user_headers,
                files={"image": ("face.jpg", face_bytes, "image/jpeg")},
            )
            profile_response.raise_for_status()
            profile_body = profile_response.json()
            profile_id = profile_body["id"]
            if "embedding" in profile_body:
                raise AssertionError("Embedding leaked from the API")

            check_in_response = await client.post(
                "/api/v1/checkins",
                files={"image": ("face.jpg", face_bytes, "image/jpeg")},
            )
            check_in_response.raise_for_status()
            check_in_body = check_in_response.json()
            check_in_ids.append(check_in_body["id"])

            history_response = await client.get("/api/v1/checkins", headers=admin_headers)
            history_response.raise_for_status()
            history = history_response.json()
            user_history_response = await client.get("/api/v1/checkins", headers=user_headers)
            user_history_response.raise_for_status()
            user_history = user_history_response.json()

            with get_session_factory()() as session:
                profile = SQLAlchemyFaceProfileRepository(session).get(profile_id)
                if profile is None:
                    raise AssertionError("Face profile was not persisted")
                records = SQLAlchemyCheckInRepository(session).list(limit=10)
                embedding_dtype = str(profile.embedding.dtype)
                embedding_dim = int(profile.embedding.size)
                embedding_norm = float(np.linalg.norm(profile.embedding))
                persisted_statuses = sorted(record.status.value for record in records)

            if check_in_body["status"] != "success" or check_in_body["user_id"] != user_id:
                raise AssertionError(f"Unexpected successful check-in: {check_in_body}")
            if sorted(item["status"] for item in history) != ["no_face", "success"]:
                raise AssertionError(f"Unexpected API history: {history}")

            result = {
                "database": database_url.split(":", 1)[0],
                "model": embedder.model_name,
                "embedding_dim": embedding_dim,
                "embedding_dtype": embedding_dtype,
                "embedding_norm": embedding_norm,
                "profile_persisted": True,
                "check_in_status": check_in_body["status"],
                "similarity_score": check_in_body["similarity_score"],
                "no_face_http_status": no_face_response.status_code,
                "history_statuses": sorted(item["status"] for item in history),
                "user_history_statuses": sorted(item["status"] for item in user_history),
                "persisted_statuses": persisted_statuses,
                "admin_login_http_status": admin_login.status_code,
                "user_login_http_status": user_login.status_code,
                "auth_me_http_status": me_response.status_code,
                "invalid_token_http_status": invalid_token_response.status_code,
                "rbac_forbidden_http_status": forbidden_response.status_code,
            }
        finally:
            if admin_headers:
                for record_id in check_in_ids:
                    await client.delete(f"/api/v1/checkins/{record_id}", headers=admin_headers)
                if profile_id is not None:
                    await client.delete(
                        f"/api/v1/face-profiles/{profile_id}", headers=admin_headers
                    )
                if user_id is not None:
                    await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
                if admin_id is not None:
                    await client.delete(f"/api/v1/users/{admin_id}", headers=admin_headers)

    # Cleanup fallback also covers a failure before login completed.
    with get_session_factory()() as session:
        check_ins = SQLAlchemyCheckInRepository(session)
        profiles = SQLAlchemyFaceProfileRepository(session)
        users = SQLAlchemyUserRepository(session)
        for record_id in check_in_ids:
            check_ins.delete(record_id)
        if profile_id is not None:
            profiles.delete(profile_id)
        if user_id is not None:
            users.delete(user_id)
        if admin_id is not None:
            users.delete(admin_id)
        session.commit()
    return result


def run_verification(database_url: str) -> dict[str, object]:
    variable_names = ("JWT_SECRET", "DATABASE_URL", "EMBEDDING_MODEL")
    previous_environment = {name: os.environ.get(name) for name in variable_names}
    try:
        os.environ["JWT_SECRET"] = "week4-verification-not-a-real-secret"
        os.environ["DATABASE_URL"] = database_url
        os.environ["EMBEDDING_MODEL"] = "buffalo_s"
        _reset_dependencies()
        command.upgrade(Config("alembic.ini"), "head")
        return asyncio.run(_exercise_api(database_url))
    finally:
        _reset_dependencies()
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        _reset_dependencies()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    print(json.dumps(run_verification(args.database_url), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
