"""Institution catalog — a school a student registers under, and the classes
that school itself offers. Distinct from the curriculum catalog's
AcademicLevel/Section (app/domain/entities/curriculum.py): a School is *which
institution*, a SchoolClass is *that institution's own class* (e.g. "6eme A"
at that school specifically). A student's own "classe" for content purposes
(subject packs, chat scoping) still comes from the shared curriculum
AcademicLevel/Section via PATCH /account/classe — SchoolClass is separate,
per-school administrative data, not wired into that flow."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class School:
    id: str
    name: str
    country: str | None
    city: str | None
    status: str  # "active" | "inactive" — no enforcement yet, just the field
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SchoolClass:
    id: str
    school_id: str
    level: str
    label: str
    created_at: datetime
