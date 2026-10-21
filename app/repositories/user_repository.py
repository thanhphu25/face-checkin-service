from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.domain.ports import UserRepository
from app.models import UserORM
from app.repositories.mappers import user_to_domain


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        row = UserORM(
            email=user.email,
            hashed_password=user.hashed_password,
            role=user.role.value,
            full_name=user.full_name,
            created_at=user.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return user_to_domain(row)

    def get(self, user_id: int) -> User | None:
        row = self._session.get(UserORM, user_id)
        return user_to_domain(row) if row is not None else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalar(select(UserORM).where(UserORM.email == email))
        return user_to_domain(row) if row is not None else None

    def list_all(self) -> list[User]:
        rows = self._session.scalars(select(UserORM).order_by(UserORM.id)).all()
        return [user_to_domain(row) for row in rows]

    def delete(self, user_id: int) -> None:
        row = self._session.get(UserORM, user_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
