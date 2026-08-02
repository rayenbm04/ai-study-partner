from dataclasses import dataclass
from datetime import datetime

TRENDS = ("up", "down", "flat")
WEAK_CONCEPT_REASONS = ("repeated_errors", "slow_response", "decay")
WEAK_CONCEPT_STATUSES = ("active", "resolved")


@dataclass(frozen=True, slots=True)
class Progress:
    """Mastery for exactly one (user, concept) pair — a leaf measurement.
    Chapter/subject-level mastery is never stored here; it's computed on read
    by aggregating child concepts' Progress rows (see
    services/progress_engine/mastery.py), per docs/ARCHITECTURE.md section 3."""

    id: str
    user_id: str
    concept_id: str
    mastery_score: float  # 0-100
    trend: str  # one of TRENDS, relative to the previous stored score
    last_updated: datetime


@dataclass(frozen=True, slots=True)
class WeakConcept:
    """A detected gap — one active row per (user, concept) at a time (see
    WeakConceptRepository docstring). `reason` records why it was flagged;
    `confidence` is a 0-1 signal strength, not a probability in any rigorous
    sense — just enough to let a UI sort/prioritize."""

    id: str
    user_id: str
    concept_id: str
    reason: str  # one of WEAK_CONCEPT_REASONS
    confidence: float  # 0-1
    status: str  # one of WEAK_CONCEPT_STATUSES
    detected_at: datetime
