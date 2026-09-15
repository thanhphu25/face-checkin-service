from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PkType


class FaceProfileORM(Base):
    __tablename__ = "face_profiles"
    __table_args__ = (CheckConstraint("embedding_dim > 0", name="dim"),)

    id: Mapped[int] = mapped_column(PkType, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        PkType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # float32 đã L2-normalize, đóng gói bằng ndarray.tobytes() — xem docs/erd.md mục 3
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    embedding_dim: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["UserORM"] = relationship(back_populates="face_profiles")  # noqa: F821
