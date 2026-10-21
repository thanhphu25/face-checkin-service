from typing import Annotated

from fastapi import APIRouter, File, Path, Query, Response, UploadFile, status

from app.api.deps import CurrentUserDependency, FaceProfileServiceDependency
from app.api.uploads import read_image_upload
from app.core.config import get_settings
from app.schemas import FaceProfileRead

router = APIRouter(prefix="/face-profiles", tags=["face-profiles"])


@router.post("", response_model=FaceProfileRead, status_code=status.HTTP_201_CREATED)
def register_face(
    image: Annotated[UploadFile, File(description="A JPEG or PNG containing exactly one face")],
    service: FaceProfileServiceDependency,
    current_user: CurrentUserDependency,
):
    payload = read_image_upload(image, max_upload_mb=get_settings().max_upload_mb)
    return service.register_face_for(current_user, payload)


@router.get("", response_model=list[FaceProfileRead])
def list_profiles(
    service: FaceProfileServiceDependency,
    current_user: CurrentUserDependency,
    user_id: Annotated[int | None, Query(gt=0)] = None,
):
    return service.list_profiles_for(current_user, user_id=user_id)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: Annotated[int, Path(gt=0)],
    service: FaceProfileServiceDependency,
    current_user: CurrentUserDependency,
) -> Response:
    service.delete_profile_for(current_user, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
