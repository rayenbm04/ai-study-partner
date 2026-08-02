import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class FlashcardReviewModel(Base):
    __tablename__ = "flashcard_reviews"
    __table_args__ = (UniqueConstraint("flashcard_id", "user_id", name="uq_flashcard_review_card_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flashcard_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("flashcards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    last_grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
