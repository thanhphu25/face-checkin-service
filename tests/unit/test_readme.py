from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")


def test_readme_contains_seven_handoff_sections() -> None:
    for section in range(1, 8):
        assert f"## {section}." in README


def test_readme_covers_compose_auth_quality_and_phase_boundaries() -> None:
    for required in (
        "docker compose config --quiet",
        "docker compose build",
        "docker compose up -d --wait",
        "docker compose logs migrate",
        "docker compose down",
        "OAuth2 form",
        "/api/v1/auth/login",
        "uv sync --python 3.12 --frozen --extra dev",
        "REQUIRE_POSTGRES_TESTS=1",
        "Tuần 6",
        "application Pha 1 chưa sử dụng Redis",
        "scripts/seed.py",
        "SEED_ADMIN_PASSWORD",
    ):
        assert required in README
