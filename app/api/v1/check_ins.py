from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Path, Query, Response, UploadFile, status

from app.api.deps import (
    AdminUserDependency,
    CheckInServiceDependency,
    CurrentUserDependency,
    UserServiceDependency,
)
from app.api.uploads import read_image_upload
from app.core.config import get_settings
from app.schemas import CheckInResult

router = APIRouter(prefix="/checkins", tags=["check-ins"])


@router.post("", response_model=CheckInResult, status_code=status.HTTP_201_CREATED)
def check_in(
    image: Annotated[UploadFile, File(description="A JPEG or PNG containing exactly one face")],
    check_ins: CheckInServiceDependency,
    users: UserServiceDependency,
) -> CheckInResult:
    payload = read_image_upload(image, max_upload_mb=get_settings().max_upload_mb)
    record = check_ins.check_in(payload)
    result = CheckInResult.model_validate(record)
    if record.user_id is not None:
        result = result.model_copy(update={"full_name": users.get_user(record.user_id).full_name})
    return result


@router.get("", response_model=list[CheckInResult])
def list_check_ins(
    service: CheckInServiceDependency,
    current_user: CurrentUserDependency,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return service.list_check_ins_for(
        current_user,
        user_id=user_id,
        start=start,
        end=end,
        limit=limit,
    )


@router.get("/{record_id}", response_model=CheckInResult)
def get_check_in(
    record_id: Annotated[int, Path(gt=0)],
    service: CheckInServiceDependency,
    current_user: CurrentUserDependency,
):
    return service.get_check_in_for(current_user, record_id)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check_in(
    record_id: Annotated[int, Path(gt=0)],
    service: CheckInServiceDependency,
    admin: AdminUserDependency,
) -> Response:
    service.delete_check_in_for(admin, record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
