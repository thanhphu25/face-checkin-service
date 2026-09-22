from pathlib import Path


def test_ci_runs_locked_quality_and_lightweight_test_gates_on_week5() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "branches: [main, week4, week5]" in workflow
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
