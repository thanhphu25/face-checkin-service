from pathlib import Path


def test_ci_runs_locked_quality_and_lightweight_test_gates_on_active_branches() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "branches: [main, week4, week5, week6]" in workflow
    assert workflow.count("uv sync --frozen --extra dev") >= 2
    assert "uv run ruff check ." in workflow
    assert "uv run ruff format --check ." in workflow
    assert "uv run lint-imports" in workflow
    assert 'uv run pytest -q -m "not real_model" tests/unit tests/api tests/integration' in workflow
    assert "RUN_REAL_MODEL_TESTS" not in workflow


def test_ci_requires_real_postgres_integration_and_builds_image() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "postgres-integration:" in workflow
    assert "image: postgres:16-alpine" in workflow
    assert 'health-cmd "pg_isready -U ci_test -d facecheckin_ci_test"' in workflow
    assert "uv run alembic upgrade head" in workflow
    assert "POSTGRES_TEST_DATABASE_URL:" in workflow
    assert 'REQUIRE_POSTGRES_TESTS: "1"' in workflow
    assert "uv run pytest -q tests/integration -p no:cacheprovider" in workflow
    assert "docker build --tag face-checkin-service:ci ." in workflow


def test_ci_runs_and_cleans_compose_on_a_clean_hosted_runner() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "compose-clean-setup:" in workflow
    assert "COMPOSE_PROJECT_NAME: facecheckin_ci_clean" in workflow
    assert "docker compose build --no-cache" in workflow
    assert "docker compose up -d --wait" in workflow
    assert "select version_num from alembic_version;" in workflow
    assert "http://127.0.0.1:58005/health" in workflow
    assert "http://127.0.0.1:58005/openapi.json" in workflow
    assert "docker compose down -v --remove-orphans" in workflow
    assert "label=com.docker.compose.project=facecheckin_ci_clean" in workflow
