import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    firstname: Mapped[str] = mapped_column(String(100), nullable=False)
    lastname: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="student", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Student profile — all nullable so pre-existing accounts stay valid.
    date_of_birth: Mapped[date | None] = mapped_column(Date(), nullable=True)
    pseudo: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    school_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True, index=True
    )
    academic_level_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("curriculum_academic_levels.id", ondelete="SET NULL"), nullable=True, index=True
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("curriculum_sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Login is never blocked on this — informational only, set by
    # AuthService.verify_email once the (stubbed, for now) verification email
    # flow is wired up.
    is_verified: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Generic account status — nothing sets this to anything but "active" yet.
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Login-attempt limiting (see AuthService.authenticate).
    failed_login_attempts: Mapped[int] = mapped_column(Integer(), default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subjects: Mapped[list["SubjectModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
