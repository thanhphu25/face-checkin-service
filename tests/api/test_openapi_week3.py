import asyncio

from app.core.config import get_settings
from app.main import create_app


def test_swagger_ui_and_week3_openapi_operations_are_available(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    app = create_app()

    async def fetch_docs():
        from httpx2 import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/docs")

    docs_response = asyncio.run(fetch_docs())
    schema = app.openapi()

    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text
    assert set(schema["paths"]) == {
        "/api/v1/users",
        "/api/v1/users/{user_id}",
        "/api/v1/face-profiles",
        "/api/v1/face-profiles/{profile_id}",
        "/api/v1/checkins",
        "/api/v1/checkins/{record_id}",
        "/health",
    }
    assert set(schema["paths"]["/api/v1/users"]) == {"get", "post"}
    assert set(schema["paths"]["/api/v1/users/{user_id}"]) == {"delete", "get"}
    assert set(schema["paths"]["/api/v1/face-profiles"]) == {"get", "post"}
    assert set(schema["paths"]["/api/v1/face-profiles/{profile_id}"]) == {"delete"}
    assert set(schema["paths"]["/api/v1/checkins"]) == {"get", "post"}
    assert set(schema["paths"]["/api/v1/checkins/{record_id}"]) == {"delete", "get"}
    assert (
        "multipart/form-data"
        in schema["paths"]["/api/v1/face-profiles"]["post"]["requestBody"]["content"]
    )
