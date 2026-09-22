from pathlib import Path

import yaml


def _compose() -> dict:
    return yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))


def test_compose_defines_only_phase_1_services() -> None:
    services = _compose()["services"]

    assert set(services) == {"app", "migrate", "postgres"}
    assert services["migrate"]["command"] == ["alembic", "upgrade", "head"]
    assert services["migrate"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert services["app"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert "healthcheck" in services["app"]
    assert "healthcheck" in services["postgres"]


def test_compose_uses_named_volumes() -> None:
    compose = _compose()
    services = compose["services"]

    assert "create_all" not in Path("compose.yaml").read_text(encoding="utf-8")
    assert services["postgres"]["volumes"] == ["postgres_data:/var/lib/postgresql/data"]
    assert services["app"]["volumes"] == ["insightface_models:/home/app/.insightface"]
    assert set(compose["volumes"]) == {"postgres_data", "insightface_models"}
