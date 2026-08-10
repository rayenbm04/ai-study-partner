import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class SecurityEventModel(Base):
    """Append-only log of security-relevant events (register, login
    success/failure, lockout, password reset, email verification) — separate
    from Python's own request/error logging (app/core/logging.py), which
    isn't queryable and isn't retained beyond the process's stdout. Kept
    deliberately minimal (no admin UI reads this yet); exists so the data is
    captured from day one rather than bolted on later."""

    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Nullable: some events (e.g. a failed login with an email that doesn't
    # exist) have no user to attach to.
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
