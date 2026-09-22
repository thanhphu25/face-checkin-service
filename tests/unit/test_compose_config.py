from pathlib import Path

import yaml


def _compose() -> dict:
    return yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))


def test_compose_defines_app_migration_postgres_and_redis() -> None:
    services = _compose()["services"]

    assert set(services) == {"app", "migrate", "postgres", "redis"}
    assert services["migrate"]["command"] == ["alembic", "upgrade", "head"]
    assert services["migrate"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert services["app"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert "healthcheck" in services["app"]
    assert "healthcheck" in services["postgres"]
    assert "healthcheck" in services["redis"]


def test_compose_keeps_redis_standby_and_uses_named_volumes() -> None:
    compose = _compose()
    services = compose["services"]

    assert "REDIS_URL" not in services["app"]["environment"]
    assert "create_all" not in Path("compose.yaml").read_text(encoding="utf-8")
    assert services["postgres"]["volumes"] == ["postgres_data:/var/lib/postgresql/data"]
    assert services["app"]["volumes"] == ["insightface_models:/home/app/.insightface"]
    assert set(compose["volumes"]) == {"postgres_data", "insightface_models"}
