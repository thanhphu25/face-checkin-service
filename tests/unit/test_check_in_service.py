from datetime import UTC, datetime

import numpy as np
import pytest

from app.domain import (
    CheckInNotFound,
    CheckInRecord,
    CheckInRepository,
    CheckInStatus,
    FaceEmbedder,
    FaceProfile,
    FaceProfileRepository,
    NoFaceDetected,
    PermissionDenied,
    Role,
    UnmatchedFace,
    User,
)
from app.services import CheckInService


class CheckInStore(CheckInRepository):
    def __init__(self) -> None:
        self.items: dict[int, CheckInRecord] = {}

    def add(self, record: CheckInRecord) -> CheckInRecord:
        saved = CheckInRecord(
            id=max(self.items, default=0) + 1,
            user_id=record.user_id,
            matched_face_profile_id=record.matched_face_profile_id,
            checkin_time=record.checkin_time,
            similarity_score=record.similarity_score,
            threshold=record.threshold,
            status=record.status,
        )
        self.items[saved.id] = saved
        return saved

    def get(self, record_id: int) -> CheckInRecord | None:
        return self.items.get(record_id)

    def list(
        self,
        *,
        user_id: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
    ) -> list[CheckInRecord]:
        records = [
            record
            for record in self.items.values()
            if (user_id is None or record.user_id == user_id)
            and (start is None or record.checkin_time >= start)
            and (end is None or record.checkin_time < end)
        ]
        return records[:limit]

    def delete(self, record_id: int) -> None:
        self.items.pop(record_id, None)


class ProfileStore(FaceProfileRepository):
    def __init__(self, profiles: list[FaceProfile]) -> None:
        self.items = {profile.id: profile for profile in profiles}

    def add(self, profile: FaceProfile) -> FaceProfile:
        self.items[profile.id] = profile
        return profile

    def get(self, profile_id: int) -> FaceProfile | None:
        return self.items.get(profile_id)

    def list_all(self) -> list[FaceProfile]:
        return list(self.items.values())

    def list_by_user(self, user_id: int) -> list[FaceProfile]:
        return [profile for profile in self.items.values() if profile.user_id == user_id]

    def delete(self, profile_id: int) -> None:
        self.items.pop(profile_id, None)


class FixedEmbedder(FaceEmbedder):
    def __init__(self, embedding: np.ndarray | None = None, *, no_face: bool = False) -> None:
        self.embedding = np.array([1.0, 0.0]) if embedding is None else embedding
        self.no_face = no_face

    @property
    def model_name(self) -> str:
        return "buffalo_s"

    def embed(self, image_bytes: bytes) -> np.ndarray:
        assert image_bytes == b"image"
        if self.no_face:
            raise NoFaceDetected()
        return self.embedding


def _profile(
    profile_id: int,
    user_id: int,
    embedding: list[float],
    *,
    model_name: str = "buffalo_s",
) -> FaceProfile:
    return FaceProfile(
        id=profile_id,
        user_id=user_id,
        embedding=np.asarray(embedding, dtype=np.float32),
        model_name=model_name,
        created_at=datetime(2026, 9, 21, 8, tzinfo=UTC),
    )


def _service(
    profiles: list[FaceProfile],
    *,
    embedding: np.ndarray | None = None,
    no_face: bool = False,
    threshold: float = 0.4,
) -> tuple[CheckInService, CheckInStore]:
    records = CheckInStore()
    service = CheckInService(
        records,
        ProfileStore(profiles),
        FixedEmbedder(embedding, no_face=no_face),
        threshold=threshold,
        clock=lambda: datetime(2026, 9, 21, 9, tzinfo=UTC),
    )
    return service, records


def test_check_in_selects_highest_cosine_match_and_saves_success() -> None:
    service, records = _service([_profile(1, 10, [0.0, 1.0]), _profile(2, 20, [1.0, 0.0])])

    result = service.check_in(b"image")

    assert result.status is CheckInStatus.SUCCESS
    assert result.user_id == 20
    assert result.matched_face_profile_id == 2
    assert result.similarity_score == pytest.approx(1.0)
    assert records.items[result.id] == result


def test_check_in_saves_unmatched_before_raising() -> None:
    service, records = _service([_profile(1, 10, [0.0, 1.0])], threshold=0.5)

    with pytest.raises(UnmatchedFace) as caught:
        service.check_in(b"image")

    record = records.items[caught.value.record_id]
    assert record.status is CheckInStatus.UNMATCHED
    assert record.user_id is None
    assert record.similarity_score == pytest.approx(0.0)


def test_check_in_saves_no_face_before_raising() -> None:
    service, records = _service([], no_face=True)

    with pytest.raises(NoFaceDetected) as caught:
        service.check_in(b"image")

    record = records.items[caught.value.record_id]
    assert record.status is CheckInStatus.NO_FACE
    assert record.similarity_score is None


def test_check_in_without_compatible_profiles_is_unmatched() -> None:
    service, records = _service([])

    with pytest.raises(UnmatchedFace) as caught:
        service.check_in(b"image")

    assert caught.value.best_score is None
    assert records.items[caught.value.record_id].status is CheckInStatus.UNMATCHED


def test_check_in_never_matches_profiles_from_other_model_or_dimension() -> None:
    profiles = [
        _profile(1, 10, [1.0, 0.0], model_name="different-model"),
        _profile(2, 20, [1.0, 0.0, 0.0]),
    ]
    service, records = _service(profiles)

    with pytest.raises(UnmatchedFace) as caught:
        service.check_in(b"image")

    assert caught.value.best_score is None
    record = records.items[caught.value.record_id]
    assert record.status is CheckInStatus.UNMATCHED
    assert record.user_id is None
    assert record.matched_face_profile_id is None


def test_history_get_list_and_delete_use_repository_port() -> None:
    service, _ = _service([_profile(1, 10, [1.0, 0.0])])
    record = service.check_in(b"image")

    assert service.get_check_in(record.id) == record
    assert service.list_check_ins(user_id=10) == [record]
    service.delete_check_in(record.id)
    assert service.list_check_ins() == []
    with pytest.raises(CheckInNotFound):
        service.get_check_in(record.id)


def test_check_in_history_is_scoped_to_owner_and_admin() -> None:
    service, _ = _service([_profile(1, 20, [1.0, 0.0])])
    record = service.check_in(b"image")
    owner = User(20, "owner@example.com", "hashed", Role.USER, "Owner", record.checkin_time)
    other = User(30, "other@example.com", "hashed", Role.USER, "Other", record.checkin_time)
    admin = User(40, "admin@example.com", "hashed", Role.ADMIN, "Admin", record.checkin_time)

    assert service.list_check_ins_for(owner, user_id=other.id) == [record]
    assert service.list_check_ins_for(other, user_id=owner.id) == []
    assert service.list_check_ins_for(admin) == [record]
    assert service.get_check_in_for(owner, record.id) == record
    assert service.get_check_in_for(admin, record.id) == record
    with pytest.raises(PermissionDenied):
        service.get_check_in_for(other, record.id)
    with pytest.raises(CheckInNotFound):
        service.get_check_in_for(other, 404)
    with pytest.raises(PermissionDenied):
        service.delete_check_in_for(other, record.id)
    with pytest.raises(PermissionDenied):
        service.delete_check_in_for(owner, record.id)

    service.delete_check_in_for(admin, record.id)
    assert service.list_check_ins_for(admin) == []
