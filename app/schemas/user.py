from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from app.domain import Role

Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class UserCreate(BaseModel):
    email: Email
    password: SecretStr = Field(min_length=8, max_length=128)
    role: Role = Role.USER
    full_name: FullName


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    email: Email
    role: Role
    full_name: FullName
    created_at: AwareDatetime
