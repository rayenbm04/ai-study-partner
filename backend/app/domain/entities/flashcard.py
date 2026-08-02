from dataclasses import dataclass
from datetime import datetime

DIFFICULTIES = ("easy", "medium", "hard")
SOURCES = ("generated", "manual")


@dataclass(frozen=True, slots=True)
class FlashcardDraft:
    """A flashcard not yet persisted — produced by the generator, consumed by
    the repository, which assigns an id."""

    question: str
    answer: str
    difficulty: str  # one of DIFFICULTIES
    tags: list[str]
    concept_id: str | None
    source: str  # one of SOURCES


@dataclass(frozen=True, slots=True)
class Flashcard:
    id: str
    subject_id: str
    concept_id: str | None
    question: str
    answer: str
    difficulty: str
    tags: list[str]
    source: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FlashcardReview:
    """SM-2 spaced-repetition state — one row per (flashcard_id, user_id),
    created on a card's first review (not at flashcard creation time, since a
    never-reviewed card is simply "due now" rather than needing a seeded row).
    """

    id: str
    flashcard_id: str
    user_id: str
    ease_factor: float
    interval_days: int
    repetitions: int
    last_grade: int | None
    last_reviewed_at: datetime | None
    next_review_date: datetime
