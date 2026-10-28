from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")
RUNNING_GUIDE = Path("docs/running.md").read_text(encoding="utf-8")


def test_readme_contains_seven_handoff_sections() -> None:
    for section in range(1, 8):
        assert f"## {section}." in README


def test_readme_covers_compose_auth_quality_and_phase_boundaries() -> None:
    for required in (
        "docker compose config --quiet",
        "docker compose build",
        "docker compose up -d --wait",
        "docker compose logs migrate",
        "OAuth2 form",
        "/api/v1/auth/login",
        "uv sync --python 3.12 --frozen --extra dev",
        "docs/benchmark-phase1.md",
        "docs/phase-2-improvements.md",
        "scripts/seed.py",
        "docs/running.md",
        "docs/running.md#seed-dữ-liệu-mẫu",
    ):
        assert required in README


def test_running_guide_covers_shutdown_seed_and_postgres_tests() -> None:
    for required in (
        "docker compose down",
        "REQUIRE_POSTGRES_TESTS=1",
        "SEED_ADMIN_PASSWORD",
    ):
        assert required in RUNNING_GUIDE
