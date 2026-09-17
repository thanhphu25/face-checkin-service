import asyncio


def test_health_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    from httpx2 import ASGITransport, AsyncClient

    from app.main import create_app

    async def request_health():
        transport = ASGITransport(app=create_app())
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
