from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PkType


class CheckInRecordORM(Base):
    __tablename__ = "check_in_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'unmatched', 'no_face')",
            name="status",
        ),
        # A successful insert must have a score. Its user can later become NULL through
        # ON DELETE SET NULL so attendance history survives identity deletion.
        CheckConstraint(
            "status <> 'success' OR similarity_score IS NOT NULL",
            name="success_score",
        ),
        Index("ix_check_in_records_user_id_checkin_time", "user_id", "checkin_time"),
        Index("ix_check_in_records_checkin_time", "checkin_time"),
    )

    id: Mapped[int] = mapped_column(PkType, Identity(always=True), primary_key=True)
    # NULL khi không khớp được ai — POST /checkins nhận ảnh của người chưa biết là ai.
    user_id: Mapped[int | None] = mapped_column(
        PkType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    matched_face_profile_id: Mapped[int | None] = mapped_column(
        PkType, ForeignKey("face_profiles.id", ondelete="SET NULL"), nullable=True
    )
    checkin_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Lưu ngưỡng tại thời điểm check-in để lịch sử cũ vẫn diễn giải được khi ngưỡng đổi.
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
