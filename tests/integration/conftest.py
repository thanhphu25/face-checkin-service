import os
from collections.abc import Iterator

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings


@pytest.fixture(params=("sqlite", "postgresql"))
def migrated_database_url(request, tmp_path, monkeypatch) -> Iterator[str]:
    """Provide a migrated, disposable database for each repository test."""
    if request.param == "sqlite":
        database_url = f"sqlite:///{(tmp_path / 'repository.db').as_posix()}"
    else:
        database_url = os.getenv("POSTGRES_TEST_DATABASE_URL")
        if not database_url:
            if os.getenv("REQUIRE_POSTGRES_TESTS") == "1":
                pytest.fail(
                    "REQUIRE_POSTGRES_TESTS=1 but POSTGRES_TEST_DATABASE_URL is not configured"
                )
            pytest.skip("POSTGRES_TEST_DATABASE_URL is not configured")
        database_name = make_url(database_url).database or ""
        if "test" not in database_name.casefold():
            pytest.fail("PostgreSQL integration tests require a database name containing 'test'")

    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002"
        yield database_url
    finally:
        engine.dispose()
        get_settings.cache_clear()


@pytest.fixture
def session(migrated_database_url: str) -> Iterator[Session]:
    """Rollback each case so PostgreSQL and SQLite tests never share rows."""
    engine = create_engine(migrated_database_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
