from fastapi import FastAPI

from app.core.config import get_settings


def create_app() -> FastAPI:
    get_settings()  # fail fast nếu thiếu biến môi trường bắt buộc
    app = FastAPI(
        title="Face Check-in Service",
        version="0.1.0",
        description="Backend check-in bằng khuôn mặt. Kiến trúc: docs/architecture.md",
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
