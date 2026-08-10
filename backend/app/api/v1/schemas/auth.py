from datetime import date, datetime, timezone

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.entities.user import User

# Deliberately permissive (allows accented characters — French pseudos are
# common here) — just no whitespace (keeps it a single "word", easy to
# display/mention) and no '@' (so a pseudo can never look like, or leak, an
# email address).
_PSEUDO_PATTERN = r"^[^\s@]{3,50}$"
_MIN_AGE_YEARS = 3  # a sanity floor, not a real age-gate — catches typos like a birth year in the future
_MAX_AGE_YEARS = 120


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    firstname: str = Field(min_length=1, max_length=100)
    lastname: str = Field(min_length=1, max_length=100)
    pseudo: str = Field(min_length=3, max_length=50, pattern=_PSEUDO_PATTERN)
    date_of_birth: date
    # Free-text for now — no school catalog exists yet (see curriculum.py for
    # what a "classe"/academic-level equivalent already does have a catalog).
    school_name: str | None = Field(default=None, max_length=200)

    @field_validator("date_of_birth")
    @classmethod
    def _validate_date_of_birth(cls, value: date) -> date:
        today = datetime.now(timezone.utc).date()
        age_years = (today - value).days / 365.25
        if value > today:
            raise ValueError("Date of birth can't be in the future.")
        if age_years > _MAX_AGE_YEARS or age_years < _MIN_AGE_YEARS:
            raise ValueError("That date of birth doesn't look right.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    firstname: str
    lastname: str
    role: str
    pseudo: str | None
    date_of_birth: date | None
    school_name: str | None
    academic_level_id: str | None
    section_id: str | None
    is_verified: bool

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            firstname=user.firstname,
            lastname=user.lastname,
            role=user.role,
            pseudo=user.pseudo,
            date_of_birth=user.date_of_birth,
            school_name=user.school_name,
            academic_level_id=user.academic_level_id,
            section_id=user.section_id,
            is_verified=user.is_verified,
        )
