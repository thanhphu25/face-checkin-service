from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.domain import CheckInStatus


class CheckInCreate(BaseModel):
    image_bytes: bytes = Field(min_length=1, repr=False)


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


class CheckInListQuery(BaseModel):
    user_id: int | None = Field(default=None, gt=0)
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None
    limit: int = Field(default=50, ge=1, le=200)

    @model_validator(mode="after")
    def validate_time_range(self) -> "CheckInListQuery":
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise ValueError("end must be later than start")
        return self
