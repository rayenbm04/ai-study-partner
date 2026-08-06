import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class SubjectModel(Base):
    __tablename__ = "subjects"
    # Partial (not a plain UniqueConstraint) so archiving a subject frees up
    # its name for reuse — otherwise removing a curriculum pack and later
    # re-applying it (or a different pack sharing a subject name) would be
    # permanently blocked by the archived row still holding the name.
    __table_args__ = (
        Index("uq_subject_user_name_active", "user_id", "name", unique=True, postgresql_where=(text("archived_at IS NULL"))),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    curriculum_subject_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("curriculum_subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped["UserModel"] = relationship(back_populates="subjects")
