from app.domain.entities.concept import Concept
from app.services.progress_engine.mastery import build_rollup, compute_trend, score_from_evidence


def _concept(id_, name, parent_id=None) -> Concept:
    return Concept(id=id_, subject_id="subj-1", name=name, description=None, parent_concept_id=parent_id)


def test_score_from_evidence_averages_flashcard_and_quiz_signals():
    score = score_from_evidence(flashcard_grades=[5, 5], answer_results=[True, False])
    # flashcard signal: 100, quiz signal: 50 -> average 75
    assert score == 75.0


def test_score_from_evidence_uses_only_flashcard_signal_when_no_quiz_evidence():
    score = score_from_evidence(flashcard_grades=[4], answer_results=[])
    assert score == 80.0  # 4/5 * 100


def test_score_from_evidence_uses_only_quiz_signal_when_no_flashcard_evidence():
    score = score_from_evidence(flashcard_grades=[], answer_results=[True, True, False])
    assert round(score, 1) == 66.7


def test_score_from_evidence_returns_none_with_no_evidence_at_all():
    assert score_from_evidence(flashcard_grades=[], answer_results=[]) is None


def test_compute_trend_flat_with_no_previous_score():
    assert compute_trend(previous_score=None, new_score=80.0) == "flat"


def test_compute_trend_up_when_score_improves_past_threshold():
    assert compute_trend(previous_score=70.0, new_score=80.0) == "up"


def test_compute_trend_down_when_score_drops_past_threshold():
    assert compute_trend(previous_score=80.0, new_score=70.0) == "down"


def test_compute_trend_flat_within_threshold_noise():
    assert compute_trend(previous_score=80.0, new_score=80.4) == "flat"


def test_compute_trend_respects_custom_thresholds():
    assert compute_trend(previous_score=80.0, new_score=85.0, up_threshold=10.0) == "flat"
    assert compute_trend(previous_score=80.0, new_score=91.0, up_threshold=10.0) == "up"


def test_build_rollup_leaf_concept_gets_its_own_score():
    concepts = [_concept("c1", "Ohm's Law")]
    tree = build_rollup(concepts, {"c1": (80.0, "up")})

    assert len(tree) == 1
    assert tree[0].concept_id == "c1"
    assert tree[0].mastery_score == 80.0
    assert tree[0].trend == "up"
    assert tree[0].children == []


def test_build_rollup_leaf_concept_with_no_evidence_is_none():
    concepts = [_concept("c1", "Untouched Concept")]
    tree = build_rollup(concepts, {})

    assert tree[0].mastery_score is None
    assert tree[0].trend is None


def test_build_rollup_parent_averages_scored_children():
    concepts = [
        _concept("chapter", "Electricity"),
        _concept("c1", "Ohm's Law", parent_id="chapter"),
        _concept("c2", "Kirchhoff's Laws", parent_id="chapter"),
    ]
    tree = build_rollup(concepts, {"c1": (80.0, "up"), "c2": (60.0, "flat")})

    assert len(tree) == 1
    chapter = tree[0]
    assert chapter.concept_id == "chapter"
    assert chapter.mastery_score == 70.0  # average of 80 and 60
    assert chapter.trend is None  # rollup nodes never carry a trend
    assert {c.concept_id for c in chapter.children} == {"c1", "c2"}


def test_build_rollup_parent_ignores_never_practiced_children():
    concepts = [
        _concept("chapter", "Electricity"),
        _concept("c1", "Ohm's Law", parent_id="chapter"),
        _concept("c2", "Untouched", parent_id="chapter"),
    ]
    tree = build_rollup(concepts, {"c1": (80.0, "up")})  # c2 has no evidence

    assert tree[0].mastery_score == 80.0  # c2 excluded from the average, not counted as 0


def test_build_rollup_parent_with_no_scored_children_is_none():
    concepts = [
        _concept("chapter", "Electricity"),
        _concept("c1", "Untouched 1", parent_id="chapter"),
        _concept("c2", "Untouched 2", parent_id="chapter"),
    ]
    tree = build_rollup(concepts, {})

    assert tree[0].mastery_score is None


def test_build_rollup_multi_level_tree():
    concepts = [
        _concept("subject", "Physics"),
        _concept("chapter", "Electricity", parent_id="subject"),
        _concept("c1", "Ohm's Law", parent_id="chapter"),
    ]
    tree = build_rollup(concepts, {"c1": (90.0, "flat")})

    subject_node = tree[0]
    assert subject_node.mastery_score == 90.0
    chapter_node = subject_node.children[0]
    assert chapter_node.mastery_score == 90.0
    leaf_node = chapter_node.children[0]
    assert leaf_node.mastery_score == 90.0
    assert leaf_node.trend == "flat"


def test_build_rollup_only_returns_top_level_roots():
    concepts = [
        _concept("root1", "Physics"),
        _concept("root2", "Chemistry"),
        _concept("c1", "Ohm's Law", parent_id="root1"),
    ]
    tree = build_rollup(concepts, {"c1": (50.0, "flat")})

    assert {node.concept_id for node in tree} == {"root1", "root2"}
