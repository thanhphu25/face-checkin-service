from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class FaceProfileCreate(BaseModel):
    image_bytes: bytes = Field(min_length=1, repr=False)


class FaceProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    model_name: str = Field(min_length=1, max_length=100)
    created_at: AwareDatetime
