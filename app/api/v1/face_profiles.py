from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Query, Response, UploadFile, status

from app.api.deps import FaceProfileServiceDependency
from app.api.uploads import read_image_upload
from app.core.config import get_settings
from app.schemas import FaceProfileRead

router = APIRouter(prefix="/face-profiles", tags=["face-profiles"])


@router.post("", response_model=FaceProfileRead, status_code=status.HTTP_201_CREATED)
def register_face(
    user_id: Annotated[int, Form(gt=0)],
    image: Annotated[UploadFile, File(description="A JPEG or PNG containing exactly one face")],
    service: FaceProfileServiceDependency,
):
    payload = read_image_upload(image, max_upload_mb=get_settings().max_upload_mb)
    return service.register_face(user_id, payload)


@router.get("", response_model=list[FaceProfileRead])
def list_profiles(
    service: FaceProfileServiceDependency,
    user_id: Annotated[int | None, Query(gt=0)] = None,
):
    return service.list_profiles(user_id=user_id)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: Annotated[int, Path(gt=0)],
    service: FaceProfileServiceDependency,
) -> Response:
    service.delete_profile(profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
