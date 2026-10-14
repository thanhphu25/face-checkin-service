"""Run a destructive-to-own-data CRUD smoke test through repository ports."""

import argparse
import logging
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain import (
    CheckInRecord,
    CheckInRepository,
    CheckInStatus,
    FaceProfile,
    FaceProfileRepository,
    Role,
    User,
    UserRepository,
)
from app.repositories import (
    SQLAlchemyCheckInRepository,
    SQLAlchemyFaceProfileRepository,
    SQLAlchemyUserRepository,
)

LOGGER = logging.getLogger("repository-smoke")


def _saved_id(value: int | None, entity_name: str) -> int:
    if value is None:
        raise AssertionError(f"{entity_name} repository did not generate an identifier")
    return value


def run_repository_smoke(session: Session) -> None:
    users: UserRepository = SQLAlchemyUserRepository(session)
    profiles: FaceProfileRepository = SQLAlchemyFaceProfileRepository(session)
    check_ins: CheckInRepository = SQLAlchemyCheckInRepository(session)
    now = datetime.now(UTC)

    user = users.add(
        User(
            id=None,
            email=f"repo-smoke-{uuid4().hex}@example.com",
            hashed_password="manual-smoke-test-only",
            role=Role.USER,
            full_name="Repository Smoke Test",
            created_at=now,
        )
    )
    user_id = _saved_id(user.id, "User")
    assert users.get(user_id) == user
    assert users.get_by_email(user.email) == user
    assert user_id in {item.id for item in users.list_all()}
    LOGGER.info("user create/read/list passed (id=%s)", user_id)

    profile = profiles.add(
        FaceProfile(
            id=None,
            user_id=user_id,
            embedding=np.array([0.6, 0.8], dtype=np.float32),
            model_name="smoke_test_model",
            created_at=now,
        )
    )
    profile_id = _saved_id(profile.id, "FaceProfile")
    loaded_profile = profiles.get(profile_id)
    assert loaded_profile is not None
    np.testing.assert_array_equal(loaded_profile.embedding, profile.embedding)
    assert profile_id in {item.id for item in profiles.list_all()}
    assert profile_id in {item.id for item in profiles.list_by_user(user_id)}
    LOGGER.info("face profile create/read/list passed (id=%s)", profile_id)

    record = check_ins.add(
        CheckInRecord(
            id=None,
            user_id=user_id,
            matched_face_profile_id=profile_id,
            checkin_time=now,
            similarity_score=1.0,
            threshold=0.4,
            status=CheckInStatus.SUCCESS,
        )
    )
    record_id = _saved_id(record.id, "CheckInRecord")
    assert check_ins.get(record_id) == record
    assert record_id in {item.id for item in check_ins.list(user_id=user_id)}
    LOGGER.info("check-in create/read/list passed (id=%s)", record_id)

    check_ins.delete(record_id)
    profiles.delete(profile_id)
    users.delete(user_id)
    assert check_ins.get(record_id) is None
    assert profiles.get(profile_id) is None
    assert users.get(user_id) is None
    LOGGER.info("delete passed for all three entities")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL; defaults to application settings.",
    )
    args = parser.parse_args()
    database_url = args.database_url or get_settings().database_url
    engine = create_engine(database_url)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    LOGGER.info("testing %s", engine.url.render_as_string(hide_password=True))

    try:
        with Session(engine) as session, session.begin():
            run_repository_smoke(session)
    finally:
        engine.dispose()

    LOGGER.info("repository CRUD smoke test passed")


if __name__ == "__main__":
    main()
