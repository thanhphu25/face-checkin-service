from fastapi import APIRouter

from app.api.v1.check_ins import router as check_ins_router
from app.api.v1.face_profiles import router as face_profiles_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(users_router)
api_router.include_router(face_profiles_router)
api_router.include_router(check_ins_router)
