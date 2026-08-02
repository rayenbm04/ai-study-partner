import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class SummaryModel(Base):
    """One row per (document_id, summary_type) — see SummaryRepository.upsert
    for why this is a cache keyed by type rather than a generation log."""

    __tablename__ = "summaries"
    __table_args__ = (UniqueConstraint("document_id", "summary_type", name="uq_summary_document_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
