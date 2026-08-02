import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ProgressModel(Base):
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_progress_user_concept"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False)
    trend: Mapped[str] = mapped_column(String(10), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
