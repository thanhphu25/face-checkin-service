from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"


class CheckInStatus(StrEnum):
    SUCCESS = "success"
    UNMATCHED = "unmatched"
    NO_FACE = "no_face"


@dataclass(frozen=True, slots=True)
class User:
    id: int | None
    email: str
    hashed_password: str
    role: Role
    full_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True, eq=False)
class FaceProfile:
    id: int | None
    user_id: int
    embedding: np.ndarray
    model_name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CheckInRecord:
    id: int | None
    user_id: int | None
    matched_face_profile_id: int | None
    checkin_time: datetime
    similarity_score: float | None
    threshold: float
    status: CheckInStatus
