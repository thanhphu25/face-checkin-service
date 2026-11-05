from io import StringIO

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from app.core.config import get_settings


@pytest.mark.parametrize("filename", ["migration.db", "migration%40.db", "migration%25.db"])
def test_initial_migration_upgrade_downgrade_upgrade(tmp_path, monkeypatch, filename) -> None:
    database_path = tmp_path / filename
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    get_settings.cache_clear()
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "check_in_records",
        "face_profiles",
        "users",
    }

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]

    command.upgrade(config, "head")
    assert "users" in inspect(engine).get_table_names()
    engine.dispose()
    get_settings.cache_clear()


@pytest.mark.parametrize("encoded_password", ["example%40pass", "example%25pass"])
def test_offline_migration_preserves_percent_encoded_postgres_url(
    monkeypatch, encoded_password
) -> None:
    database_url = f"postgresql+psycopg://app:{encoded_password}@localhost/migration_test"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_SECRET", "migration-test-only-secret")
    get_settings.cache_clear()
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)

    try:
        command.upgrade(config, "head", sql=True)

        assert config.get_main_option("sqlalchemy.url") == database_url
        assert "CREATE TABLE users" in output.getvalue()
        assert "ALTER TABLE check_in_records" in output.getvalue()
    finally:
        get_settings.cache_clear()
