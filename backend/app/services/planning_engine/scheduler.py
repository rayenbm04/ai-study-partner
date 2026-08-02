"""Pure study-plan scheduling — no I/O, no repository calls, so it's fully
unit-testable without a database. Turns "these concepts, this exam date,
this many minutes a day" into a day-by-day list of sessions.

Priority: a concept the student has never touched, or one flagged as a weak
concept by the progress engine, is scheduled before one that's simply
lower-scored — an active, detected gap should jump the queue ahead of a
concept that's merely "somewhat mastered." Everything else is ordered by
mastery score ascending (weakest first).

Sessions cycle through the priority-ordered concept list round-robin: the
first pass through the list is exposure (reading for never-touched
concepts, flashcards otherwise), the second pass tests with a quiz, and
later passes alternate — a light approximation of spaced revisiting rather
than a full second scheduling algorithm layered on top of this one.

If an exam date is set and the plan spans more than one day, the final day
is reserved as a full-subject review/mock-exam session instead of being
filled with the normal per-concept rotation.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.entities.study_plan import StudyPlanItemDraft

DEFAULT_SESSION_MINUTES = 25
DEFAULT_PLAN_DAYS = 14  # used when no exam_date is given


@dataclass(frozen=True, slots=True)
class ConceptPriority:
    concept_id: str
    subject_id: str
    urgency: float  # lower = more urgent


def rank_concepts(
    concepts: list[tuple[str, str, float | None]], weak_concept_ids: set[str]
) -> list[ConceptPriority]:
    """concepts: (concept_id, subject_id, mastery_score-or-None) tuples.
    Weak-flagged and never-touched concepts sort first; everything else by
    mastery score ascending."""

    def urgency_of(concept_id: str, score: float | None) -> float:
        if concept_id in weak_concept_ids:
            return -2.0
        if score is None:
            return -1.0
        return score

    ranked = sorted(concepts, key=lambda c: urgency_of(c[0], c[2]))
    return [
        ConceptPriority(concept_id=concept_id, subject_id=subject_id, urgency=urgency_of(concept_id, score))
        for concept_id, subject_id, score in ranked
    ]


def build_plan_items(
    *,
    priorities: list[ConceptPriority],
    start_date: date,
    exam_date: date | None,
    daily_minutes_available: int,
    session_minutes: int = DEFAULT_SESSION_MINUTES,
    default_plan_days: int = DEFAULT_PLAN_DAYS,
) -> list[StudyPlanItemDraft]:
    if not priorities:
        return []

    total_days = max(1, (exam_date - start_date).days) if exam_date else default_plan_days
    sessions_per_day = max(1, daily_minutes_available // session_minutes)

    # Reserve the last day for a full review/mock exam if there's room for one.
    reserve_exam_day = exam_date is not None and total_days > 1
    rotation_days = total_days - 1 if reserve_exam_day else total_days
    total_slots = max(1, rotation_days * sessions_per_day)

    items: list[StudyPlanItemDraft] = []
    for slot in range(total_slots):
        priority = priorities[slot % len(priorities)]
        pass_number = slot // len(priorities)  # 0 = first exposure, 1 = first quiz, ...

        if pass_number == 0:
            activity = "reading" if priority.urgency == -1.0 else "flashcards"
        elif pass_number % 2 == 1:
            activity = "quiz"
        else:
            activity = "flashcards"

        day_offset = slot // sessions_per_day
        items.append(
            StudyPlanItemDraft(
                subject_id=priority.subject_id,
                concept_id=priority.concept_id,
                scheduled_date=start_date + timedelta(days=day_offset),
                activity_type=activity,
                duration_minutes=session_minutes,
            )
        )

    if reserve_exam_day:
        review_date = exam_date - timedelta(days=1)
        for subject_id in dict.fromkeys(p.subject_id for p in priorities):  # de-duplicated, order-preserving
            items.append(
                StudyPlanItemDraft(
                    subject_id=subject_id,
                    concept_id=None,
                    scheduled_date=review_date,
                    activity_type="exam",
                    duration_minutes=daily_minutes_available,
                )
            )

    return items
