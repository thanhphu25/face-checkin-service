from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain import CheckInStatus


class CheckInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    user_id: int | None = Field(default=None, gt=0)
    matched_face_profile_id: int | None = Field(default=None, gt=0)
    checkin_time: AwareDatetime
    similarity_score: float | None = Field(default=None, ge=-1, le=1)
    threshold: float = Field(ge=-1, le=1)
    status: CheckInStatus


class CheckInResult(CheckInRead):
    full_name: str | None = None
