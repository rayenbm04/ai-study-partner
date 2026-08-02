from datetime import datetime, timedelta, timezone

import pytest

from app.services.flashcard_engine import sm2

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_initial_state_is_due_immediately():
    state = sm2.initial_state(now=_NOW)

    assert state.ease_factor == sm2.INITIAL_EASE_FACTOR
    assert state.interval_days == 0
    assert state.repetitions == 0
    assert state.next_review_date == _NOW


def test_first_successful_review_sets_interval_to_one_day():
    state = sm2.review(ease_factor=2.5, interval_days=0, repetitions=0, quality=4, reviewed_at=_NOW)

    assert state.repetitions == 1
    assert state.interval_days == 1
    assert state.next_review_date == _NOW + timedelta(days=1)


def test_second_successful_review_sets_interval_to_six_days():
    state = sm2.review(ease_factor=2.5, interval_days=1, repetitions=1, quality=4, reviewed_at=_NOW)

    assert state.repetitions == 2
    assert state.interval_days == 6


def test_third_successful_review_multiplies_interval_by_ease_factor():
    state = sm2.review(ease_factor=2.5, interval_days=6, repetitions=2, quality=4, reviewed_at=_NOW)

    assert state.repetitions == 3
    assert state.interval_days == round(6 * 2.5)  # 15


def test_lapse_resets_repetitions_and_interval_but_not_ease_factor_to_scratch():
    state = sm2.review(ease_factor=2.5, interval_days=15, repetitions=3, quality=1, reviewed_at=_NOW)

    assert state.repetitions == 0
    assert state.interval_days == 1
    # Ease factor still drops per the formula (quality=1 is a poor recall) —
    # just the streak resets, not the long-run difficulty estimate.
    assert state.ease_factor < 2.5


def test_quality_five_increases_ease_factor_by_one_tenth():
    state = sm2.review(ease_factor=2.5, interval_days=1, repetitions=1, quality=5, reviewed_at=_NOW)

    assert state.ease_factor == pytest.approx(2.6)


def test_quality_four_leaves_ease_factor_unchanged():
    state = sm2.review(ease_factor=2.5, interval_days=1, repetitions=1, quality=4, reviewed_at=_NOW)

    assert state.ease_factor == pytest.approx(2.5)


def test_quality_three_decreases_ease_factor():
    state = sm2.review(ease_factor=2.5, interval_days=1, repetitions=1, quality=3, reviewed_at=_NOW)

    assert state.ease_factor == pytest.approx(2.36)


def test_ease_factor_never_drops_below_minimum():
    ease_factor = 2.5
    interval_days = 0
    repetitions = 0
    for _ in range(20):
        state = sm2.review(
            ease_factor=ease_factor, interval_days=interval_days, repetitions=repetitions,
            quality=0, reviewed_at=_NOW,
        )
        ease_factor, interval_days, repetitions = state.ease_factor, state.interval_days, state.repetitions

    assert ease_factor == pytest.approx(sm2.MINIMUM_EASE_FACTOR)
    assert ease_factor >= sm2.MINIMUM_EASE_FACTOR


@pytest.mark.parametrize("quality", [-1, 6, 10, -5])
def test_invalid_quality_raises(quality):
    with pytest.raises(ValueError):
        sm2.review(ease_factor=2.5, interval_days=1, repetitions=1, quality=quality, reviewed_at=_NOW)


def test_next_review_date_is_reviewed_at_plus_interval():
    state = sm2.review(ease_factor=2.5, interval_days=6, repetitions=2, quality=5, reviewed_at=_NOW)

    assert state.next_review_date == _NOW + timedelta(days=state.interval_days)
