"""Weak-concept detection — flags concepts a student appears to be
struggling with, from the three signals named in docs/ARCHITECTURE.md
section 3:

- repeated_errors: enough quiz/exam questions on this concept have been
  answered wrong, often enough, that it doesn't look like a fluke.
- slow_response: quiz/exam questions on this concept take noticeably longer
  to answer than a configured baseline — a proxy for "not fluent yet" even
  when the answer ends up correct.
- decay: the concept was reasonably mastered before and has since measurably
  dropped. The SM-2 flashcard schedule already handles the *reminder* side
  of forgetting (it requeues the card); this is the *diagnostic* side —
  surface it as a gap in the weak-concepts list, not just a due flashcard.

Each check is independent and pure (no I/O); only the strongest signal is
kept as the single active flag per concept (see ProgressService), so the UI
shows one clear reason rather than a pile of overlapping ones.
"""
from dataclasses import dataclass

MIN_ERROR_COUNT = 2              # need at least this many wrong answers before "repeated" means anything
ERROR_RATE_THRESHOLD = 0.5        # >= 50% wrong among this concept's answers
SLOW_RESPONSE_SECONDS = 60         # average time above this counts as "slow"
DECAY_DROP_THRESHOLD = 15.0        # point drop from the previous score to count as decay
DECAY_MIN_PREVIOUS_SCORE = 60.0    # only counts as decay if it used to be reasonably mastered


@dataclass(frozen=True, slots=True)
class WeaknessSignal:
    reason: str  # one of WEAK_CONCEPT_REASONS
    confidence: float  # 0-1, a heuristic strength score — not a calibrated probability


def detect_repeated_errors(
    answer_results: list[bool],
    *,
    min_error_count: int = MIN_ERROR_COUNT,
    error_rate_threshold: float = ERROR_RATE_THRESHOLD,
) -> WeaknessSignal | None:
    if len(answer_results) < min_error_count:
        return None
    wrong = sum(1 for correct in answer_results if not correct)
    if wrong < min_error_count:
        return None
    rate = wrong / len(answer_results)
    if rate < error_rate_threshold:
        return None
    return WeaknessSignal(reason="repeated_errors", confidence=round(min(rate, 1.0), 2))


def detect_slow_response(
    response_times: list[int], *, slow_response_seconds: float = SLOW_RESPONSE_SECONDS
) -> WeaknessSignal | None:
    if not response_times:
        return None
    average = sum(response_times) / len(response_times)
    if average < slow_response_seconds:
        return None
    # confidence grows with how far past the baseline the average sits, capped at 1.0
    confidence = min(1.0, (average - slow_response_seconds) / slow_response_seconds + 0.5)
    return WeaknessSignal(reason="slow_response", confidence=round(confidence, 2))


def detect_decay(
    *,
    previous_score: float | None,
    new_score: float | None,
    drop_threshold: float = DECAY_DROP_THRESHOLD,
    min_previous_score: float = DECAY_MIN_PREVIOUS_SCORE,
) -> WeaknessSignal | None:
    if previous_score is None or new_score is None:
        return None
    if previous_score < min_previous_score:
        return None
    drop = previous_score - new_score
    if drop < drop_threshold:
        return None
    confidence = min(1.0, drop / previous_score)
    return WeaknessSignal(reason="decay", confidence=round(confidence, 2))


def detect(
    *,
    answer_results: list[bool],
    response_times: list[int],
    previous_score: float | None,
    new_score: float | None,
    min_error_count: int = MIN_ERROR_COUNT,
    error_rate_threshold: float = ERROR_RATE_THRESHOLD,
    slow_response_seconds: float = SLOW_RESPONSE_SECONDS,
    decay_drop_threshold: float = DECAY_DROP_THRESHOLD,
    decay_min_previous_score: float = DECAY_MIN_PREVIOUS_SCORE,
) -> WeaknessSignal | None:
    """Runs all three checks and returns the strongest signal (highest
    confidence), or None if nothing crossed a threshold. Order of preference
    on a tie: repeated_errors > decay > slow_response, since a concrete wrong
    answer is a stronger signal than a timing heuristic. Thresholds are
    parameters (not hardcoded) so ProgressService can wire them to settings."""
    candidates = [
        signal
        for signal in (
            detect_repeated_errors(
                answer_results, min_error_count=min_error_count, error_rate_threshold=error_rate_threshold
            ),
            detect_decay(
                previous_score=previous_score,
                new_score=new_score,
                drop_threshold=decay_drop_threshold,
                min_previous_score=decay_min_previous_score,
            ),
            detect_slow_response(response_times, slow_response_seconds=slow_response_seconds),
        )
        if signal is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda signal: signal.confidence)
