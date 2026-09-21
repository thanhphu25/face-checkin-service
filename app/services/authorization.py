from app.domain.entities import Role, User
from app.domain.errors import PermissionDenied


def require_admin(requester: User) -> None:
    if requester.role is not Role.ADMIN:
        raise PermissionDenied("Administrator role is required")


def require_owner_or_admin(requester: User, *, owner_id: int | None) -> None:
    if requester.role is Role.ADMIN:
        return
    if requester.id is None or owner_id != requester.id:
        raise PermissionDenied("You do not own this resource")


def scope_user_id(requester: User, *, requested_user_id: int | None) -> int | None:
    if requester.role is Role.ADMIN:
        return requested_user_id
    if requester.id is None:
        raise PermissionDenied("A persisted user is required")
    return requester.id
