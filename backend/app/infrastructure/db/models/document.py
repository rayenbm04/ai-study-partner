import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    document_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    chapter_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("curriculum_chapters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lesson_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("curriculum_lessons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    processing_step: Mapped[str | None] = mapped_column(String(30), nullable=True)
    processing_progress: Mapped[int | None] = mapped_column(Integer, nullable=True)

    chunks: Mapped[list["ChunkModel"]] = relationship(back_populates="document", cascade="all, delete-orphan")
