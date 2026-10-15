import asyncio
from datetime import UTC, datetime

import numpy as np

from app.api.deps import get_check_in_service, get_face_profile_service, get_user_service
from app.core.config import get_settings
from app.domain import CheckInRecord, CheckInStatus, FaceProfile, Role, User
from app.main import create_app

NOW = datetime(2026, 9, 21, 10, tzinfo=UTC)


class UserServiceSpy:
    def __init__(self) -> None:
        self.user = User(1, "person@example.com", "hidden", Role.USER, "Person", NOW)
        self.created_password: str | None = None
        self.deleted: list[int] = []

    def create_user(self, **values) -> User:
        self.created_password = values["password"]
        return self.user

    def list_users(self) -> list[User]:
        return [self.user]

    def get_user(self, user_id: int) -> User:
        assert user_id == 1
        return self.user

    def delete_user(self, user_id: int) -> None:
        self.deleted.append(user_id)


class FaceProfileServiceSpy:
    def __init__(self) -> None:
        self.profile = FaceProfile(2, 1, np.ones(2, dtype=np.float32), "buffalo_s", NOW)
        self.registered: tuple[int, bytes] | None = None
        self.deleted: list[int] = []

    def register_face(self, user_id: int, image_bytes: bytes) -> FaceProfile:
        self.registered = (user_id, image_bytes)
        return self.profile

    def list_profiles(self, *, user_id: int | None = None) -> list[FaceProfile]:
        assert user_id in (None, 1)
        return [self.profile]

    def delete_profile(self, profile_id: int) -> None:
        self.deleted.append(profile_id)


class CheckInServiceSpy:
    def __init__(self) -> None:
        self.record = CheckInRecord(3, 1, 2, NOW, 0.91, 0.4, CheckInStatus.SUCCESS)
        self.image: bytes | None = None
        self.deleted: list[int] = []

    def check_in(self, image_bytes: bytes) -> CheckInRecord:
        self.image = image_bytes
        return self.record

    def list_check_ins(self, **filters) -> list[CheckInRecord]:
        assert filters["limit"] == 10
        return [self.record]

    def get_check_in(self, record_id: int) -> CheckInRecord:
        assert record_id == 3
        return self.record

    def delete_check_in(self, record_id: int) -> None:
        self.deleted.append(record_id)


def test_resource_routers_expose_validated_crud_without_biometric_leaks(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    users = UserServiceSpy()
    profiles = FaceProfileServiceSpy()
    check_ins = CheckInServiceSpy()
    app = create_app()
    app.dependency_overrides[get_user_service] = lambda: users
    app.dependency_overrides[get_face_profile_service] = lambda: profiles
    app.dependency_overrides[get_check_in_service] = lambda: check_ins

    async def exercise_api() -> list:
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = []
            responses.append(
                await client.post(
                    "/api/v1/users",
                    json={
                        "email": "person@example.com",
                        "password": "strong-password",
                        "full_name": "Person",
                    },
                )
            )
            responses.append(await client.get("/api/v1/users"))
            responses.append(await client.get("/api/v1/users/1"))
            responses.append(await client.delete("/api/v1/users/1"))
            image = {"image": ("face.png", b"png-bytes", "image/png")}
            responses.append(
                await client.post(
                    "/api/v1/face-profiles",
                    data={"user_id": "1"},
                    files=image,
                )
            )
            responses.append(await client.get("/api/v1/face-profiles?user_id=1"))
            responses.append(await client.delete("/api/v1/face-profiles/2"))
            responses.append(await client.post("/api/v1/checkins", files=image))
            responses.append(await client.get("/api/v1/checkins?limit=10"))
            responses.append(await client.get("/api/v1/checkins/3"))
            responses.append(await client.delete("/api/v1/checkins/3"))
            return responses

    responses = asyncio.run(exercise_api())

    assert [response.status_code for response in responses] == [
        201,
        200,
        200,
        204,
        201,
        200,
        204,
        201,
        200,
        200,
        204,
    ]
    assert users.created_password == "strong-password"
    assert "hashed_password" not in responses[0].json()
    assert profiles.registered == (1, b"png-bytes")
    assert "embedding" not in responses[4].json()
    assert check_ins.image == b"png-bytes"
    assert responses[7].json()["full_name"] == "Person"
    assert users.deleted == [1]
    assert profiles.deleted == [2]
    assert check_ins.deleted == [3]


def test_uploads_reject_wrong_media_type_before_service(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    profiles = FaceProfileServiceSpy()
    app = create_app()
    app.dependency_overrides[get_face_profile_service] = lambda: profiles

    async def upload_text():
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/face-profiles",
                data={"user_id": "1"},
                files={"image": ("face.txt", b"not-image", "text/plain")},
            )

    response = asyncio.run(upload_text())

    assert response.status_code == 400
    assert response.json()["error"] == "InvalidImage"
    assert profiles.registered is None
