from pathlib import Path


def test_ci_runs_tests_and_all_quality_gates_on_week4() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "branches: [main, week4]" in workflow
    assert "uv sync --frozen --extra dev" in workflow
    assert "uv run pytest -q" in workflow
    assert "uv run ruff check ." in workflow
    assert "uv run ruff format --check ." in workflow
    assert "uv run lint-imports" in workflow
    assert "JWT_SECRET: ci-test-secret-khong-dung-that" in workflow
