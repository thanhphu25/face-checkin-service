from pathlib import Path

ADR_FILES = sorted(Path("docs/adr").glob("*.md"))


def test_adrs_use_consistent_structure_and_change_conditions() -> None:
    assert len(ADR_FILES) == 5
    for path in ADR_FILES:
        content = path.read_text(encoding="utf-8")
        assert "- Status: Accepted" in content
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Alternatives considered" in content
        assert "## Consequences" in content
        assert "xem lại" in content.casefold()


def test_adrs_record_the_implemented_phase_1_boundaries() -> None:
    content = "\n".join(path.read_text(encoding="utf-8") for path in ADR_FILES)

    for decision in (
        "PostgreSQL",
        "SQLite",
        "SQLAlchemy",
        "Alembic",
        "OAuth2PasswordBearer",
        "Argon2id",
        "PBKDF2",
        "buffalo_s",
        "float32",
        "L2-normalized",
        "pgvector",
        "FAISS",
        "Redis",
        "nearest-rank",
        "một worker",
    ):
        assert decision in content
