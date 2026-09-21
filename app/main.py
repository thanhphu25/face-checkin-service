from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.v1 import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    get_settings()  # fail fast nếu thiếu biến môi trường bắt buộc
    app = FastAPI(
        title="Face Check-in Service",
        version="0.1.0",
        description="Backend check-in bằng khuôn mặt. Kiến trúc: docs/architecture.md",
    )
    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
