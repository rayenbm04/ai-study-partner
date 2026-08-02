from datetime import date, datetime, timezone

import pytest

from app.domain.entities.quiz import QuizQuestionDraft
from app.core.exceptions import (
    EmptyStudyPlanError,
    InvalidStudyPlanItemStatusError,
    StudyPlanItemNotFoundError,
    StudyPlanNotFoundError,
    SubjectNotFoundError,
)
from app.services.planning_engine.planning_service import PlanningService
from app.services.progress_engine.progress_service import ProgressService
from app.services.subject_service import SubjectService
from tests.unit.fakes import (
    FakeConceptRepository,
    FakeFlashcardRepository,
    FakeFlashcardReviewRepository,
    FakeProgressRepository,
    FakeQuizAttemptRepository,
    FakeQuizRepository,
    FakeStudentAnswerRepository,
    FakeStudyPlanRepository,
    FakeSubjectRepository,
    FakeWeakConceptRepository,
)


async def _build():
    subject_repo = FakeSubjectRepository()
    subject_service = SubjectService(subject_repo)
    concept_repo = FakeConceptRepository()
    quiz_repo = FakeQuizRepository()
    quiz_attempt_repo = FakeQuizAttemptRepository()
    student_answer_repo = FakeStudentAnswerRepository()
    progress_service = ProgressService(
        subject_service=subject_service,
        concept_repo=concept_repo,
        flashcard_repo=FakeFlashcardRepository(subject_repo=subject_repo),
        flashcard_review_repo=FakeFlashcardReviewRepository(),
        quiz_repo=quiz_repo,
        quiz_attempt_repo=quiz_attempt_repo,
        student_answer_repo=student_answer_repo,
        progress_repo=FakeProgressRepository(),
        weak_concept_repo=FakeWeakConceptRepository(),
    )
    study_plan_repo = FakeStudyPlanRepository()
    service = PlanningService(
        study_plan_repo=study_plan_repo, subject_service=subject_service, progress_service=progress_service
    )
    repos = {
        "subject_repo": subject_repo,
        "concept_repo": concept_repo,
        "study_plan_repo": study_plan_repo,
        "quiz_repo": quiz_repo,
        "quiz_attempt_repo": quiz_attempt_repo,
        "student_answer_repo": student_answer_repo,
    }
    return service, repos


async def _seed_subject_with_concepts(repos, *, user_id="user-1", names=("Ohm's Law", "Kirchhoff's Law")):
    subject = await repos["subject_repo"].create(user_id=user_id, name="Physics", description=None, color=None, icon=None)
    concepts = [await repos["concept_repo"].create(subject_id=subject.id, name=n, description=None) for n in names]
    return subject, concepts


async def test_generate_raises_when_subject_not_owned():
    service, repos = await _build()
    subject, _concepts = await _seed_subject_with_concepts(repos)

    with pytest.raises(SubjectNotFoundError):
        await service.generate(
            user_id="someone-else", name="Plan", subject_ids=[subject.id], exam_date=None,
            daily_minutes_available=30,
        )


async def test_generate_raises_when_no_concepts_in_selected_subjects():
    service, repos = await _build()
    subject = await repos["subject_repo"].create(
        user_id="user-1", name="Empty Subject", description=None, color=None, icon=None
    )

    with pytest.raises(EmptyStudyPlanError):
        await service.generate(
            user_id="user-1", name="Plan", subject_ids=[subject.id], exam_date=None, daily_minutes_available=30
        )


async def test_generate_creates_plan_with_items_covering_all_concepts():
    service, repos = await _build()
    subject, concepts = await _seed_subject_with_concepts(repos)

    plan = await service.generate(
        user_id="user-1", name="Midterm Prep", subject_ids=[subject.id], exam_date=None,
        daily_minutes_available=25, start_date=date(2026, 1, 1),
    )

    assert plan.name == "Midterm Prep"
    assert plan.status == "active"
    items = await service.get_items("user-1", plan.id)
    assert len(items) > 0
    concept_ids_covered = {item.concept_id for item in items}
    assert concept_ids_covered == {c.id for c in concepts}


async def test_generate_reserves_exam_review_day_when_exam_date_set():
    service, repos = await _build()
    subject, _concepts = await _seed_subject_with_concepts(repos, names=("Only Concept",))

    plan = await service.generate(
        user_id="user-1", name="Exam Prep", subject_ids=[subject.id], exam_date=date(2026, 1, 10),
        daily_minutes_available=25, start_date=date(2026, 1, 1),
    )

    items = await service.get_items("user-1", plan.id)
    exam_items = [i for i in items if i.activity_type == "exam"]
    assert len(exam_items) == 1
    assert exam_items[0].scheduled_date == date(2026, 1, 9)


async def test_get_owned_raises_for_plan_not_owned():
    service, repos = await _build()
    subject, _concepts = await _seed_subject_with_concepts(repos)
    plan = await service.generate(
        user_id="user-1", name="Plan", subject_ids=[subject.id], exam_date=None, daily_minutes_available=30
    )

    with pytest.raises(StudyPlanNotFoundError):
        await service.get_owned("someone-else", plan.id)


async def test_update_item_status_success():
    service, repos = await _build()
    subject, _concepts = await _seed_subject_with_concepts(repos)
    plan = await service.generate(
        user_id="user-1", name="Plan", subject_ids=[subject.id], exam_date=None, daily_minutes_available=30
    )
    items = await service.get_items("user-1", plan.id)

    updated = await service.update_item_status("user-1", items[0].id, status="done")

    assert updated.status == "done"


async def test_update_item_status_raises_for_invalid_status():
    service, repos = await _build()
    subject, _concepts = await _seed_subject_with_concepts(repos)
    plan = await service.generate(
        user_id="user-1", name="Plan", subject_ids=[subject.id], exam_date=None, daily_minutes_available=30
    )
    items = await service.get_items("user-1", plan.id)

    with pytest.raises(InvalidStudyPlanItemStatusError):
        await service.update_item_status("user-1", items[0].id, status="bogus")


async def test_update_item_status_raises_for_item_not_found():
    service, _repos = await _build()

    with pytest.raises(StudyPlanItemNotFoundError):
        await service.update_item_status("user-1", "nonexistent-item", status="done")


async def test_update_item_status_raises_when_plan_not_owned_by_caller():
    service, repos = await _build()
    subject, _concepts = await _seed_subject_with_concepts(repos)
    plan = await service.generate(
        user_id="user-1", name="Plan", subject_ids=[subject.id], exam_date=None, daily_minutes_available=30
    )
    items = await service.get_items("user-1", plan.id)

    with pytest.raises(StudyPlanNotFoundError):
        await service.update_item_status("someone-else", items[0].id, status="done")


async def test_generate_prioritizes_weak_concepts_first():
    service, repos = await _build()
    subject, concepts = await _seed_subject_with_concepts(repos, names=("Weak Concept", "Strong Concept"))
    weak_concept, strong_concept = concepts

    # Give weak_concept a flagged weakness via repeated wrong quiz answers; strong_concept stays untouched.
    quiz_repo = repos["quiz_repo"]
    attempt_repo = repos["quiz_attempt_repo"]
    answer_repo = repos["student_answer_repo"]

    quiz_obj = await quiz_repo.create(
        subject_id=subject.id, user_id="user-1", title="Q", kind="quiz", difficulty="easy",
        topics=[], duration_minutes=None, style=None,
    )
    questions = await quiz_repo.bulk_create_questions(
        quiz_id=quiz_obj.id,
        drafts=[
            QuizQuestionDraft(
                type="mcq", question=f"q{i}", options=["a", "b"], correct_answer="a", explanation=None,
                points=1, difficulty="easy", concept_id=weak_concept.id,
            )
            for i in range(3)
        ],
    )
    attempt = await attempt_repo.create(quiz_id=quiz_obj.id, user_id="user-1")
    now = datetime.now(timezone.utc)
    for i, question in enumerate(questions):
        await answer_repo.upsert(
            quiz_attempt_id=attempt.id, quiz_question_id=question.id, answer="b",
            is_correct=(i == 2), time_spent_seconds=5, submitted_at=now,
        )

    plan = await service.generate(
        user_id="user-1", name="Plan", subject_ids=[subject.id], exam_date=None,
        daily_minutes_available=25, start_date=date(2026, 1, 1),
    )
    items = await service.get_items("user-1", plan.id)
    # weak_concept is flagged weak (urgency -2.0), strong_concept is merely untouched
    # (urgency -1.0) -> weak_concept must be scheduled first.
    assert items[0].concept_id == weak_concept.id
    assert items[1].concept_id == strong_concept.id
