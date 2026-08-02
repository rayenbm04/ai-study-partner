from dataclasses import dataclass
from datetime import date, datetime

STUDY_PLAN_STATUSES = ("active", "completed", "archived")
ACTIVITY_TYPES = ("reading", "flashcards", "quiz", "exam")
STUDY_PLAN_ITEM_STATUSES = ("pending", "done", "skipped")


@dataclass(frozen=True, slots=True)
class StudyPlanItemDraft:
    """A scheduled session not yet persisted — produced by scheduler.py,
    consumed by the repository, which assigns an id and links it to a plan."""

    subject_id: str
    concept_id: str | None  # None for a subject-wide review/exam session
    scheduled_date: date
    activity_type: str  # one of ACTIVITY_TYPES
    duration_minutes: int


@dataclass(frozen=True, slots=True)
class StudyPlan:
    id: str
    user_id: str
    name: str
    exam_date: date | None
    daily_minutes_available: int
    status: str  # one of STUDY_PLAN_STATUSES
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StudyPlanItem:
    id: str
    study_plan_id: str
    subject_id: str
    concept_id: str | None
    scheduled_date: date
    activity_type: str
    duration_minutes: int
    status: str  # one of STUDY_PLAN_ITEM_STATUSES
