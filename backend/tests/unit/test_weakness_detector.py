from app.services.progress_engine.weakness_detector import (
    detect,
    detect_decay,
    detect_repeated_errors,
    detect_slow_response,
)


def test_detect_repeated_errors_flags_high_error_rate():
    signal = detect_repeated_errors([False, False, True])
    assert signal is not None
    assert signal.reason == "repeated_errors"
    assert signal.confidence == round(2 / 3, 2)


def test_detect_repeated_errors_ignores_low_error_rate():
    assert detect_repeated_errors([True, True, True, False]) is None


def test_detect_repeated_errors_requires_minimum_count():
    # 1 wrong out of 1 is 100% wrong, but below the minimum sample size
    assert detect_repeated_errors([False]) is None


def test_detect_repeated_errors_respects_custom_thresholds():
    # 2 wrong out of 3 = 67% error rate
    assert detect_repeated_errors([False, False, True], error_rate_threshold=0.3) is not None
    assert detect_repeated_errors([False, False, True], error_rate_threshold=0.9) is None


def test_detect_slow_response_flags_above_baseline():
    signal = detect_slow_response([90, 90], slow_response_seconds=60)
    assert signal is not None
    assert signal.reason == "slow_response"


def test_detect_slow_response_ignores_fast_answers():
    assert detect_slow_response([10, 20], slow_response_seconds=60) is None


def test_detect_slow_response_ignores_empty_input():
    assert detect_slow_response([]) is None


def test_detect_decay_flags_significant_drop_from_high_baseline():
    signal = detect_decay(previous_score=90.0, new_score=60.0, drop_threshold=15.0, min_previous_score=60.0)
    assert signal is not None
    assert signal.reason == "decay"


def test_detect_decay_ignores_small_drop():
    assert detect_decay(previous_score=90.0, new_score=85.0, drop_threshold=15.0) is None


def test_detect_decay_ignores_concepts_never_well_mastered():
    # dropped a lot, but was never actually "mastered" to begin with
    assert detect_decay(previous_score=40.0, new_score=10.0, min_previous_score=60.0) is None


def test_detect_decay_requires_both_scores():
    assert detect_decay(previous_score=None, new_score=50.0) is None
    assert detect_decay(previous_score=90.0, new_score=None) is None


def test_detect_returns_none_when_nothing_crosses_a_threshold():
    result = detect(
        answer_results=[True, True], response_times=[5, 5], previous_score=80.0, new_score=82.0
    )
    assert result is None


def test_detect_prefers_repeated_errors_over_slow_response():
    result = detect(
        answer_results=[False, False, False],
        response_times=[200, 200],  # would also trigger slow_response
        previous_score=None,
        new_score=None,
    )
    assert result.reason == "repeated_errors"


def test_detect_falls_back_to_slow_response_alone():
    result = detect(
        answer_results=[True, True], response_times=[200, 200], previous_score=None, new_score=None
    )
    assert result.reason == "slow_response"


def test_detect_picks_decay_over_slow_response_when_stronger():
    result = detect(
        answer_results=[],
        response_times=[61],  # just barely over the 60s baseline -> low confidence
        previous_score=95.0,
        new_score=20.0,  # huge drop from a well-mastered concept -> high confidence
    )
    assert result.reason == "decay"
