from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import PBKDF2PasswordHasher
from app.domain.errors import DomainError
from app.domain.ports import FaceEmbedder, PasswordHasher
from app.ml import InsightFaceEmbedder
from app.repositories import (
    SQLAlchemyCheckInRepository,
    SQLAlchemyFaceProfileRepository,
    SQLAlchemyUserRepository,
)
from app.services import CheckInService, FaceProfileService, UserService


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    connect_args = (
        {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    )
    return create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


def get_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    except DomainError:
        # Expected check-in failures are audit events and must remain persisted.
        session.commit()
        raise
    except BaseException:
        session.rollback()
        raise
    else:
        session.commit()
    finally:
        session.close()


@lru_cache
def get_embedder() -> FaceEmbedder:
    settings = get_settings()
    return InsightFaceEmbedder(model_name=settings.embedding_model)


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return PBKDF2PasswordHasher()


SessionDependency = Annotated[Session, Depends(get_session)]
EmbedderDependency = Annotated[FaceEmbedder, Depends(get_embedder)]
HasherDependency = Annotated[PasswordHasher, Depends(get_password_hasher)]


def get_user_service(session: SessionDependency, hasher: HasherDependency) -> UserService:
    return UserService(SQLAlchemyUserRepository(session), hasher)


def get_face_profile_service(
    session: SessionDependency,
    embedder: EmbedderDependency,
) -> FaceProfileService:
    return FaceProfileService(
        SQLAlchemyFaceProfileRepository(session),
        SQLAlchemyUserRepository(session),
        embedder,
    )


def get_check_in_service(
    session: SessionDependency,
    embedder: EmbedderDependency,
) -> CheckInService:
    return CheckInService(
        SQLAlchemyCheckInRepository(session),
        SQLAlchemyFaceProfileRepository(session),
        embedder,
        threshold=get_settings().similarity_threshold,
    )


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
FaceProfileServiceDependency = Annotated[FaceProfileService, Depends(get_face_profile_service)]
CheckInServiceDependency = Annotated[CheckInService, Depends(get_check_in_service)]
