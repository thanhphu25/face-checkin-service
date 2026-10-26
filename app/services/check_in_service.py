from collections.abc import Callable
from datetime import UTC, datetime
from typing import NoReturn

import numpy as np

from app.domain.embeddings import normalize_embedding
from app.domain.entities import CheckInRecord, CheckInStatus, User
from app.domain.errors import CheckInNotFound, NoFaceDetected, UnmatchedFace
from app.domain.ports import CheckInRepository, FaceEmbedder, FaceProfileRepository
from app.services.authorization import require_admin, require_owner_or_admin, scope_user_id


class CheckInService:
    def __init__(
        self,
        check_ins: CheckInRepository,
        profiles: FaceProfileRepository,
        embedder: FaceEmbedder,
        *,
        threshold: float,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not -1.0 <= threshold <= 1.0:
            raise ValueError("Similarity threshold must be between -1 and 1")
        self._check_ins = check_ins
        self._profiles = profiles
        self._embedder = embedder
        self._threshold = threshold
        self._clock = clock or (lambda: datetime.now(UTC))

    def check_in(self, image_bytes: bytes) -> CheckInRecord:
        try:
            query = normalize_embedding(self._embedder.embed(image_bytes))
        except NoFaceDetected as exc:
            # Lưu lịch sử trước khi trả lỗi để lần check-in này vẫn được ghi nhận.
            record = self._save(
                status=CheckInStatus.NO_FACE,
                user_id=None,
                profile_id=None,
                score=None,
            )
            raise NoFaceDetected(str(exc), record_id=record.id) from exc

        # Chỉ so sánh các vector cùng model và kích thước với ảnh đầu vào.
        candidates = [
            profile
            for profile in self._profiles.list_all()
            if profile.model_name == self._embedder.model_name
            and profile.embedding.ndim == 1
            and profile.embedding.shape == query.shape
        ]
        if not candidates:
            self._raise_unmatched(None)

        # Vector đã chuẩn hóa: tích vô hướng là cosine; clip sai số về [-1, 1].
        matrix = np.stack([normalize_embedding(profile.embedding) for profile in candidates])
        scores = np.clip(matrix @ query, -1.0, 1.0)
        best_index = int(np.argmax(scores))
        best_score = float(scores[best_index])
        best_profile = candidates[best_index]

        if best_score < self._threshold:
            self._raise_unmatched(best_score)

        return self._save(
            status=CheckInStatus.SUCCESS,
            user_id=best_profile.user_id,
            profile_id=best_profile.id,
            score=best_score,
        )

    def get_check_in(self, record_id: int) -> CheckInRecord:
        record = self._check_ins.get(record_id)
        if record is None:
            raise CheckInNotFound(f"Check-in {record_id} was not found")
        return record

    def get_check_in_for(self, requester: User, record_id: int) -> CheckInRecord:
        record = self.get_check_in(record_id)
        require_owner_or_admin(requester, owner_id=record.user_id)
        return record

    def list_check_ins(
        self,
        *,
        user_id: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
    ) -> list[CheckInRecord]:
        return self._check_ins.list(user_id=user_id, start=start, end=end, limit=limit)

    def list_check_ins_for(
        self,
        requester: User,
        *,
        user_id: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
    ) -> list[CheckInRecord]:
        scoped_user_id = scope_user_id(requester, requested_user_id=user_id)
        return self.list_check_ins(
            user_id=scoped_user_id,
            start=start,
            end=end,
            limit=limit,
        )

    def delete_check_in(self, record_id: int) -> None:
        self.get_check_in(record_id)
        self._check_ins.delete(record_id)

    def delete_check_in_for(self, requester: User, record_id: int) -> None:
        record = self.get_check_in(record_id)
        require_admin(requester)
        self._check_ins.delete(record.id)

    def _save(
        self,
        *,
        status: CheckInStatus,
        user_id: int | None,
        profile_id: int | None,
        score: float | None,
    ) -> CheckInRecord:
        return self._check_ins.add(
            CheckInRecord(
                id=None,
                user_id=user_id,
                matched_face_profile_id=profile_id,
                checkin_time=self._clock(),
                similarity_score=score,
                threshold=self._threshold,
                status=status,
            )
        )

    def _raise_unmatched(self, best_score: float | None) -> NoReturn:
        record = self._save(
            status=CheckInStatus.UNMATCHED,
            user_id=None,
            profile_id=None,
            score=best_score,
        )
        raise UnmatchedFace(best_score, record_id=record.id)
