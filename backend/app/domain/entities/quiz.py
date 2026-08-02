from dataclasses import dataclass
from datetime import datetime

KINDS = ("quiz", "exam")
QUESTION_TYPES = ("mcq", "true_false", "short_answer", "calculation", "fill_blank")
DIFFICULTIES = ("easy", "medium", "hard")
# mcq/true_false/fill_blank are graded by exact/normalized string match; short_answer
# and calculation need an LLM judgement call since exact match is too strict for
# open-ended phrasing — see services/quiz_engine/grading.py.
AUTO_GRADABLE_TYPES = ("mcq", "true_false", "fill_blank")


@dataclass(frozen=True, slots=True)
class QuizQuestionDraft:
    """A quiz question not yet persisted — produced by the generator, consumed
    by the repository, which assigns an id and links it to a quiz."""

    type: str  # one of QUESTION_TYPES
    question: str
    options: list[str] | None
    correct_answer: str
    explanation: str | None
    points: int
    difficulty: str  # one of DIFFICULTIES
    concept_id: str | None


@dataclass(frozen=True, slots=True)
class Quiz:
    id: str
    subject_id: str
    user_id: str
    title: str
    kind: str  # one of KINDS
    difficulty: str
    topics: list[str]
    duration_minutes: int | None  # exams only
    style: str | None  # e.g. "past-exam"
    created_at: datetime


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    id: str
    quiz_id: str
    concept_id: str | None
    type: str
    question: str
    options: list[str] | None
    correct_answer: str
    explanation: str | None
    points: int
    difficulty: str


@dataclass(frozen=True, slots=True)
class QuizAttempt:
    id: str
    quiz_id: str
    user_id: str
    started_at: datetime
    completed_at: datetime | None
    score: float | None  # 0-100, set once the attempt is submitted


@dataclass(frozen=True, slots=True)
class StudentAnswer:
    """One row per (quiz_attempt_id, quiz_question_id) — resubmitting an
    answer before the attempt is finalized overwrites the prior one rather
    than logging every keystroke-level change."""

    id: str
    quiz_attempt_id: str
    quiz_question_id: str
    answer: str
    is_correct: bool | None
    time_spent_seconds: int | None
    submitted_at: datetime
