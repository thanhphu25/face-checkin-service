from app.api.v1.check_ins import router as check_ins_router
from app.api.v1.face_profiles import router as face_profiles_router
from app.api.v1.router import api_router
from app.api.v1.users import router as users_router


def test_v1_resource_routers_have_stable_prefixes_and_no_business_handlers() -> None:
    assert api_router.prefix == "/api/v1"
    assert users_router.prefix == "/users"
    assert face_profiles_router.prefix == "/face-profiles"
    assert check_ins_router.prefix == "/checkins"
    assert users_router.routes == []
    assert face_profiles_router.routes == []
    assert check_ins_router.routes == []
