from pathlib import Path

from scripts.export_openapi import DEFAULT_OUTPUT, build_openapi, render


def test_exported_openapi_matches_the_running_application() -> None:
    committed = Path(DEFAULT_OUTPUT).read_text(encoding="utf-8")

    assert committed == render(build_openapi()), (
        "docs/openapi.json is stale; re-run: uv run python -m scripts.export_openapi"
    )


def test_exported_openapi_documents_every_handover_endpoint() -> None:
    document = build_openapi()

    assert document["info"]["title"] == "Face Check-in Service"
    assert set(document["paths"]) == {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/users",
        "/api/v1/users/{user_id}",
        "/api/v1/face-profiles",
        "/api/v1/face-profiles/{profile_id}",
        "/api/v1/checkins",
        "/api/v1/checkins/{record_id}",
    }
    assert "OAuth2PasswordBearer" in document["components"]["securitySchemes"]
    # The check-in endpoint stays public; the history read stays protected.
    assert "security" not in document["paths"]["/api/v1/checkins"]["post"]
    assert document["paths"]["/api/v1/checkins"]["get"]["security"]
