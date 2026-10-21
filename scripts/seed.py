"""Seed reproducible sample data for demos, handover and benchmark runs.

The script is idempotent: running it twice leaves the same rows behind. Passwords
are read from the environment so no credential ever reaches Git, and the sample
face comes from the picture bundled with the InsightFace wheel.
"""

import argparse
import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import Argon2PasswordHasher
from app.domain import (
    CheckInRecord,
    CheckInRepository,
    CheckInStatus,
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
from app.services import FaceProfileService, UserService

LOGGER = logging.getLogger("seed")

ADMIN_EMAIL = "admin.sample@example.test"
ADMIN_PASSWORD_ENV = "SEED_ADMIN_PASSWORD"
USER_EMAIL = "user.sample@example.test"
USER_PASSWORD_ENV = "SEED_USER_PASSWORD"

# Fixed offsets from the seeding moment keep the sample history ordered and
# reproducible without hard-coding a calendar date that ages badly.
SAMPLE_HISTORY: tuple[tuple[int, CheckInStatus, float | None], ...] = (
    (52, CheckInStatus.SUCCESS, 0.82),
    (28, CheckInStatus.UNMATCHED, 0.21),
    (4, CheckInStatus.NO_FACE, None),
)


def _required_password(variable: str) -> str:
    password = os.environ.get(variable, "")
    if len(password.strip()) < 12:
        raise SystemExit(
            f"{variable} must be set to at least 12 characters before seeding. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(24))"'
        )
    return password


def _ensure_user(
    users: UserService,
    repository: UserRepository,
    *,
    email: str,
    password_env: str,
    full_name: str,
    role: Role,
) -> User:
    existing = repository.get_by_email(UserService.normalize_email(email))
    if existing is not None:
        LOGGER.info("user already present, left untouched: %s (id=%s)", email, existing.id)
        return existing
    created = users.create_user(
        email=email,
        password=_required_password(password_env),
        full_name=full_name,
        role=role,
    )
    LOGGER.info("user created: %s (id=%s, role=%s)", email, created.id, role.value)
    return created


def _ensure_face_profile(
    profiles: FaceProfileRepository,
    service: FaceProfileService,
    *,
    user_id: int,
) -> int | None:
    existing = profiles.list_by_user(user_id)
    if existing:
        LOGGER.info("face profile already present for user %s (id=%s)", user_id, existing[0].id)
        return existing[0].id

    from scripts.sample_images import face_image_bytes

    profile = service.register_face(user_id, face_image_bytes())
    LOGGER.info(
        "face profile created: id=%s model=%s dim=%s",
        profile.id,
        profile.model_name,
        profile.embedding.shape[0],
    )
    return profile.id


def _ensure_history(
    check_ins: CheckInRepository,
    *,
    user_id: int,
    profile_id: int | None,
    threshold: float,
    now: datetime,
) -> int:
    if check_ins.list(user_id=user_id, limit=1):
        LOGGER.info("check-in history already present for user %s, left untouched", user_id)
        return 0

    created = 0
    for minutes_ago, status, score in SAMPLE_HISTORY:
        matched = status is CheckInStatus.SUCCESS
        check_ins.add(
            CheckInRecord(
                id=None,
                user_id=user_id if matched else None,
                matched_face_profile_id=profile_id if matched else None,
                checkin_time=now - timedelta(minutes=minutes_ago),
                similarity_score=score,
                threshold=threshold,
                status=status,
            )
        )
        created += 1
    LOGGER.info("check-in history created: %s records", created)
    return created


def seed(session: Session, *, with_face_profile: bool = True) -> dict[str, object]:
    settings = get_settings()
    user_repository = SQLAlchemyUserRepository(session)
    profile_repository = SQLAlchemyFaceProfileRepository(session)
    check_in_repository = SQLAlchemyCheckInRepository(session)
    users = UserService(user_repository, Argon2PasswordHasher())

    admin = _ensure_user(
        users,
        user_repository,
        email=ADMIN_EMAIL,
        password_env=ADMIN_PASSWORD_ENV,
        full_name="Admin Mau",
        role=Role.ADMIN,
    )
    member = _ensure_user(
        users,
        user_repository,
        email=USER_EMAIL,
        password_env=USER_PASSWORD_ENV,
        full_name="User Mau",
        role=Role.USER,
    )
    if member.id is None:
        raise SystemExit("Sample user was not persisted")

    profile_id: int | None = None
    if with_face_profile:
        from app.ml import InsightFaceEmbedder

        profile_id = _ensure_face_profile(
            profile_repository,
            FaceProfileService(
                profile_repository,
                user_repository,
                InsightFaceEmbedder(model_name=settings.embedding_model),
            ),
            user_id=member.id,
        )
    else:
        LOGGER.info("face profile skipped; check-in requests will report unmatched")

    history_created = _ensure_history(
        check_in_repository,
        user_id=member.id,
        profile_id=profile_id,
        threshold=settings.similarity_threshold,
        now=datetime.now(UTC),
    )
    return {
        "admin_id": admin.id,
        "user_id": member.id,
        "face_profile_id": profile_id,
        "history_created": history_created,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL; defaults to application settings.",
    )
    parser.add_argument(
        "--skip-face-profile",
        action="store_true",
        help="Seed users and history only, without loading the embedding model.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    database_url = args.database_url or get_settings().database_url
    engine = create_engine(database_url)
    LOGGER.info("seeding %s", engine.url.render_as_string(hide_password=True))
    try:
        with Session(engine) as session, session.begin():
            summary = seed(session, with_face_profile=not args.skip_face_profile)
    finally:
        engine.dispose()
    LOGGER.info("seed complete: %s", summary)


if __name__ == "__main__":
    main()
