from datetime import date

from app.services.planning_engine.scheduler import build_plan_items, rank_concepts


def test_rank_concepts_puts_weak_and_untouched_before_scored():
    concepts = [
        ("scored-high", "sub-1", 90.0),
        ("weak", "sub-1", 80.0),  # scored high but flagged weak -> most urgent
        ("untouched", "sub-1", None),
        ("scored-low", "sub-1", 20.0),
    ]
    ranked = rank_concepts(concepts, weak_concept_ids={"weak"})

    ids_in_order = [p.concept_id for p in ranked]
    assert ids_in_order[0] == "weak"
    assert ids_in_order[1] == "untouched"
    assert ids_in_order[2:] == ["scored-low", "scored-high"]


def test_rank_concepts_orders_scored_concepts_ascending():
    concepts = [("a", "sub-1", 70.0), ("b", "sub-1", 10.0), ("c", "sub-1", 40.0)]
    ranked = rank_concepts(concepts, weak_concept_ids=set())
    assert [p.concept_id for p in ranked] == ["b", "c", "a"]


def test_build_plan_items_returns_empty_for_no_priorities():
    assert build_plan_items(
        priorities=[], start_date=date(2026, 1, 1), exam_date=None, daily_minutes_available=30
    ) == []


def test_build_plan_items_distributes_across_default_plan_length():
    ranked = rank_concepts([("c1", "sub-1", None), ("c2", "sub-1", None)], weak_concept_ids=set())
    items = build_plan_items(
        priorities=ranked, start_date=date(2026, 1, 1), exam_date=None, daily_minutes_available=25,
        session_minutes=25, default_plan_days=14,
    )
    # 1 session/day * 14 days = 14 slots, no exam day reserved since exam_date is None
    assert len(items) == 14
    assert all(item.activity_type != "exam" for item in items)
    assert items[0].scheduled_date == date(2026, 1, 1)
    assert items[-1].scheduled_date == date(2026, 1, 14)


def test_build_plan_items_first_pass_uses_reading_for_untouched_and_flashcards_for_scored():
    ranked = rank_concepts(
        [("untouched", "sub-1", None), ("scored", "sub-1", 55.0)], weak_concept_ids=set()
    )
    items = build_plan_items(
        priorities=ranked, start_date=date(2026, 1, 1), exam_date=None, daily_minutes_available=50,
        session_minutes=25,
    )
    # slot 0 -> untouched (urgency -1.0), slot 1 -> scored
    assert items[0].activity_type == "reading"
    assert items[1].activity_type == "flashcards"


def test_build_plan_items_reserves_final_day_for_exam_review():
    ranked = rank_concepts([("c1", "sub-1", 50.0)], weak_concept_ids=set())
    exam_date = date(2026, 1, 10)
    items = build_plan_items(
        priorities=ranked, start_date=date(2026, 1, 1), exam_date=exam_date, daily_minutes_available=25,
        session_minutes=25,
    )
    exam_items = [i for i in items if i.activity_type == "exam"]
    assert len(exam_items) == 1
    assert exam_items[0].scheduled_date == date(2026, 1, 9)  # day before exam_date
    assert exam_items[0].concept_id is None
    assert exam_items[0].subject_id == "sub-1"
    assert all(i.scheduled_date < exam_items[0].scheduled_date for i in items if i.activity_type != "exam")


def test_build_plan_items_no_exam_day_reserved_when_plan_is_single_day():
    ranked = rank_concepts([("c1", "sub-1", 50.0)], weak_concept_ids=set())
    exam_date = date(2026, 1, 1)  # same as start_date -> total_days == 1, no room to reserve
    items = build_plan_items(
        priorities=ranked, start_date=date(2026, 1, 1), exam_date=exam_date, daily_minutes_available=25,
        session_minutes=25,
    )
    assert all(i.activity_type != "exam" for i in items)


def test_build_plan_items_respects_daily_minutes_available_for_sessions_per_day():
    ranked = rank_concepts([("c1", "sub-1", None), ("c2", "sub-1", None)], weak_concept_ids=set())
    items = build_plan_items(
        priorities=ranked, start_date=date(2026, 1, 1), exam_date=None, daily_minutes_available=100,
        session_minutes=25, default_plan_days=3,
    )
    # 100 // 25 = 4 sessions/day * 3 days = 12 slots
    assert len(items) == 12
    day_1_items = [i for i in items if i.scheduled_date == date(2026, 1, 1)]
    assert len(day_1_items) == 4
