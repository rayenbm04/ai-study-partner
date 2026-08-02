"""The SM-2 spaced-repetition algorithm (SuperMemo-2), unchanged from the
original 1987 specification — these constants and formulas are the published
algorithm, not tunable app config, so they live here as code rather than in
settings.

Quality is graded 0-5 on review ("how well did you recall this card"):
0-2 counts as a lapse (card resets), 3-5 counts as a successful recall with
increasing confidence. Every function here is pure — no I/O, no repository
calls — so it's fully unit-testable without a database or fakes.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

INITIAL_EASE_FACTOR = 2.5
MINIMUM_EASE_FACTOR = 1.3
MINIMUM_QUALITY_FOR_SUCCESS = 3


@dataclass(frozen=True, slots=True)
class SM2State:
    ease_factor: float
    interval_days: int
    repetitions: int
    next_review_date: datetime


def initial_state(*, now: datetime) -> SM2State:
    """A card that has never been reviewed is due immediately."""
    return SM2State(ease_factor=INITIAL_EASE_FACTOR, interval_days=0, repetitions=0, next_review_date=now)


def review(
    *, ease_factor: float, interval_days: int, repetitions: int, quality: int, reviewed_at: datetime
) -> SM2State:
    """Computes the next SM-2 state after a review graded `quality` (0-5)."""
    if not 0 <= quality <= 5:
        raise ValueError(f"quality must be between 0 and 5, got {quality}")

    if quality < MINIMUM_QUALITY_FOR_SUCCESS:
        # A lapse resets the repetition streak, but not the ease factor —
        # the card comes back tomorrow rather than in months.
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)

    new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease_factor = max(new_ease_factor, MINIMUM_EASE_FACTOR)

    return SM2State(
        ease_factor=new_ease_factor,
        interval_days=new_interval,
        repetitions=new_repetitions,
        next_review_date=reviewed_at + timedelta(days=new_interval),
    )
