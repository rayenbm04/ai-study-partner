import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class FlashcardModel(Base):
    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
