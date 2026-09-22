from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import CheckInRecord
from app.domain.ports import CheckInRepository
from app.models import CheckInRecordORM
from app.repositories.mappers import check_in_to_domain


class SQLAlchemyCheckInRepository(CheckInRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: CheckInRecord) -> CheckInRecord:
        row = CheckInRecordORM(
            user_id=record.user_id,
            matched_face_profile_id=record.matched_face_profile_id,
            checkin_time=record.checkin_time,
            similarity_score=record.similarity_score,
            threshold=record.threshold,
            status=record.status.value,
        )
        self._session.add(row)
        self._session.flush()
        return check_in_to_domain(row)

    def get(self, record_id: int) -> CheckInRecord | None:
        row = self._session.get(CheckInRecordORM, record_id)
        return check_in_to_domain(row) if row is not None else None

    def list(
        self,
        *,
        user_id: int | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
    ) -> list[CheckInRecord]:
        if limit < 1:
            raise ValueError("Check-in list limit must be positive")
        statement = select(CheckInRecordORM)
        if user_id is not None:
            statement = statement.where(CheckInRecordORM.user_id == user_id)
        if start is not None:
            statement = statement.where(CheckInRecordORM.checkin_time >= start)
        if end is not None:
            statement = statement.where(CheckInRecordORM.checkin_time < end)
        statement = statement.order_by(
            CheckInRecordORM.checkin_time.desc(), CheckInRecordORM.id.desc()
        ).limit(limit)
        return [check_in_to_domain(row) for row in self._session.scalars(statement).all()]

    def delete(self, record_id: int) -> None:
        row = self._session.get(CheckInRecordORM, record_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
