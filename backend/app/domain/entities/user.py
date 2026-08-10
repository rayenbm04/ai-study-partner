from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    firstname: str
    lastname: str
    hashed_password: str
    role: str
    created_at: datetime
    # Student profile fields — all optional so existing accounts (created
    # before these existed) stay valid without a backfill.
    pseudo: str | None = None
    date_of_birth: date | None = None
    school_id: str | None = None
    academic_level_id: str | None = None
    section_id: str | None = None
    # Email verification is now wired up (see AuthService.verify_email /
    # request_password_reset / reset_password) but login is never blocked on
    # it — is_verified is informational, not a gate.
    is_verified: bool = False
    email_verified_at: datetime | None = None
    # Generic account status (spec calls for one on the core USER table) —
    # nothing sets it to anything but "active" yet; exists for a future
    # suspend/ban admin action.
    status: str = "active"
    last_login_at: datetime | None = None
    # Login-attempt limiting (see AuthService.authenticate).
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
