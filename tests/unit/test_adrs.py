from pathlib import Path

DECISIONS_DOCUMENT = Path("docs/architecture.md")


def test_adrs_use_consistent_structure_and_change_conditions() -> None:
    content = DECISIONS_DOCUMENT.read_text(encoding="utf-8")
    assert "quyết định đã chấp nhận" in content
    decisions_section = content.split("\n## Quyết định thiết kế\n", 1)[1]
    decisions = decisions_section.split("\n### ")[1:]
    assert len(decisions) == 5
    for decision in decisions:
        assert "**Lựa chọn:**" in decision
        assert "**Lý do và đánh đổi:**" in decision
        assert "**Khi cần xem lại:**" in decision


def test_adrs_record_the_implemented_phase_1_boundaries() -> None:
    content = DECISIONS_DOCUMENT.read_text(encoding="utf-8")

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
