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
    school_name: str | None = None
    academic_level_id: str | None = None
    section_id: str | None = None
    # Email verification isn't enforced anywhere yet (no email-sending
    # integration exists in this codebase) — these fields exist so that
    # feature can be wired up later without another migration.
    is_verified: bool = False
    email_verified_at: datetime | None = None
