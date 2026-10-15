from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.api.deps import UserServiceDependency
from app.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(request: UserCreate, service: UserServiceDependency):
    return service.create_user(
        email=request.email,
        password=request.password.get_secret_value(),
        full_name=request.full_name,
        role=request.role,
    )


@router.get("", response_model=list[UserRead])
def list_users(service: UserServiceDependency):
    return service.list_users()


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: Annotated[int, Path(gt=0)],
    service: UserServiceDependency,
):
    return service.get_user(user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: Annotated[int, Path(gt=0)],
    service: UserServiceDependency,
) -> Response:
    service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
