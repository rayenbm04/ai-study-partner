from datetime import datetime, timezone

import pytest

from app.core.exceptions import SubjectNotFoundError
from app.domain.entities.flashcard import FlashcardDraft
from app.domain.entities.quiz import QuizQuestionDraft
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
    FakeSubjectRepository,
    FakeWeakConceptRepository,
)

_NOW = datetime.now(timezone.utc)


async def _build(**overrides):
    subject_repo = FakeSubjectRepository()
    subject_service = SubjectService(subject_repo)
    service_repos = dict(
        concept_repo=FakeConceptRepository(),
        flashcard_repo=FakeFlashcardRepository(subject_repo=subject_repo),
        flashcard_review_repo=FakeFlashcardReviewRepository(),
        quiz_repo=FakeQuizRepository(),
        quiz_attempt_repo=FakeQuizAttemptRepository(),
        student_answer_repo=FakeStudentAnswerRepository(),
        progress_repo=FakeProgressRepository(),
        weak_concept_repo=FakeWeakConceptRepository(),
    )
    service = ProgressService(subject_service=subject_service, **service_repos, **overrides)
    return service, {**service_repos, "subject_repo": subject_repo}


async def _seed_subject_and_concept(repos, *, user_id="user-1", concept_name="Ohm's Law"):
    subject = await repos["subject_repo"].create(user_id=user_id, name="Physics", description=None, color=None, icon=None)
    concept = await repos["concept_repo"].create(subject_id=subject.id, name=concept_name, description=None)
    return subject, concept


async def _seed_flashcard_review(repos, *, subject_id, concept_id, user_id="user-1", grade):
    card = (
        await repos["flashcard_repo"].bulk_create(
            subject_id=subject_id,
            drafts=[
                FlashcardDraft(
                    question="q", answer="a", difficulty="easy", tags=[], concept_id=concept_id, source="generated"
                )
            ],
        )
    )[0]
    await repos["flashcard_review_repo"].upsert(
        flashcard_id=card.id, user_id=user_id, ease_factor=2.5, interval_days=1, repetitions=1,
        last_grade=grade, last_reviewed_at=_NOW, next_review_date=_NOW,
    )
    return card


async def _seed_quiz_answers(repos, *, subject_id, concept_id, user_id="user-1", results, time_spent_seconds=5):
    quiz = await repos["quiz_repo"].create(
        subject_id=subject_id, user_id=user_id, title="Quiz", kind="quiz", difficulty="easy",
        topics=[], duration_minutes=None, style=None,
    )
    questions = await repos["quiz_repo"].bulk_create_questions(
        quiz_id=quiz.id,
        drafts=[
            QuizQuestionDraft(
                type="mcq", question=f"q{i}", options=["a", "b"], correct_answer="a",
                explanation=None, points=1, difficulty="easy", concept_id=concept_id,
            )
            for i in range(len(results))
        ],
    )
    attempt = await repos["quiz_attempt_repo"].create(quiz_id=quiz.id, user_id=user_id)
    for question, is_correct in zip(questions, results):
        await repos["student_answer_repo"].upsert(
            quiz_attempt_id=attempt.id, quiz_question_id=question.id, answer="a" if is_correct else "b",
            is_correct=is_correct, time_spent_seconds=time_spent_seconds, submitted_at=_NOW,
        )
    return quiz, questions, attempt


async def test_get_progress_computes_score_from_flashcard_and_quiz_evidence():
    service, repos = await _build()
    subject, concept = await _seed_subject_and_concept(repos)
    await _seed_flashcard_review(repos, subject_id=subject.id, concept_id=concept.id, grade=5)
    await _seed_quiz_answers(repos, subject_id=subject.id, concept_id=concept.id, results=[True])

    tree = await service.get_progress(user_id="user-1", subject_id=subject.id)

    assert len(tree) == 1
    node = tree[0]
    assert node.concept_id == concept.id
    assert node.mastery_score == 100.0  # flashcard signal 100 + quiz signal 100 -> 100
    assert node.trend == "flat"  # first time scored

    stored = await repos["progress_repo"].get_by_user_and_concept("user-1", concept.id)
    assert stored.mastery_score == 100.0


async def test_get_progress_leaves_untouched_concepts_with_no_score():
    service, repos = await _build()
    subject, _concept = await _seed_subject_and_concept(repos)
    await repos["concept_repo"].create(subject_id=subject.id, name="Never Practiced", description=None)

    tree = await service.get_progress(user_id="user-1", subject_id=subject.id)

    assert all(node.mastery_score is None for node in tree)


async def test_get_progress_trend_reflects_change_between_recomputes():
    service, repos = await _build()
    subject, concept = await _seed_subject_and_concept(repos)
    card = await _seed_flashcard_review(repos, subject_id=subject.id, concept_id=concept.id, grade=2)

    first = await service.get_progress(user_id="user-1", subject_id=subject.id)
    assert first[0].mastery_score == 40.0
    assert first[0].trend == "flat"

    # same card, reviewed again with a better grade — not a new card
    await repos["flashcard_review_repo"].upsert(
        flashcard_id=card.id, user_id="user-1", ease_factor=2.5, interval_days=6, repetitions=2,
        last_grade=5, last_reviewed_at=_NOW, next_review_date=_NOW,
    )
    second = await service.get_progress(user_id="user-1", subject_id=subject.id)
    assert second[0].mastery_score == 100.0
    assert second[0].trend == "up"


async def test_get_progress_raises_when_subject_not_owned():
    service, repos = await _build()
    subject, _concept = await _seed_subject_and_concept(repos)

    with pytest.raises(SubjectNotFoundError):
        await service.get_progress(user_id="someone-else", subject_id=subject.id)


async def test_get_weak_concepts_flags_repeated_errors():
    service, repos = await _build()
    subject, concept = await _seed_subject_and_concept(repos)
    await _seed_quiz_answers(repos, subject_id=subject.id, concept_id=concept.id, results=[False, False, True])

    weak = await service.get_weak_concepts(user_id="user-1", subject_id=subject.id)

    assert len(weak) == 1
    assert weak[0].concept_id == concept.id
    assert weak[0].reason == "repeated_errors"
    assert weak[0].status == "active"


async def test_weak_concept_resolves_once_errors_stop():
    service, repos = await _build()
    subject, concept = await _seed_subject_and_concept(repos)
    quiz, questions, attempt = await _seed_quiz_answers(
        repos, subject_id=subject.id, concept_id=concept.id, results=[False, False, True]
    )
    before = await service.get_weak_concepts(user_id="user-1", subject_id=subject.id)
    assert len(before) == 1

    for question in questions:
        await repos["student_answer_repo"].upsert(
            quiz_attempt_id=attempt.id, quiz_question_id=question.id, answer="a", is_correct=True,
            time_spent_seconds=5, submitted_at=_NOW,
        )

    after = await service.get_weak_concepts(user_id="user-1", subject_id=subject.id)
    assert after == []


async def test_get_weak_concepts_ignores_healthy_concepts():
    service, repos = await _build()
    subject, concept = await _seed_subject_and_concept(repos)
    await _seed_quiz_answers(repos, subject_id=subject.id, concept_id=concept.id, results=[True, True, True])

    weak = await service.get_weak_concepts(user_id="user-1", subject_id=subject.id)

    assert weak == []


async def test_get_weak_concepts_raises_when_subject_not_owned():
    service, repos = await _build()
    subject, _concept = await _seed_subject_and_concept(repos)

    with pytest.raises(SubjectNotFoundError):
        await service.get_weak_concepts(user_id="someone-else", subject_id=subject.id)


async def test_progress_service_respects_custom_weak_concept_thresholds():
    service, repos = await _build(weak_min_error_count=10)  # effectively disables the check
    subject, concept = await _seed_subject_and_concept(repos)
    await _seed_quiz_answers(repos, subject_id=subject.id, concept_id=concept.id, results=[False, False, True])

    weak = await service.get_weak_concepts(user_id="user-1", subject_id=subject.id)

    assert weak == []


async def test_weak_concepts_are_isolated_between_subjects():
    service, repos = await _build()
    subject, concept = await _seed_subject_and_concept(repos)
    await _seed_quiz_answers(repos, subject_id=subject.id, concept_id=concept.id, results=[False, False, True])

    other_subject, other_concept = await _seed_subject_and_concept(repos, concept_name="Unrelated")

    weak_for_other_subject = await service.get_weak_concepts(user_id="user-1", subject_id=other_subject.id)
    assert weak_for_other_subject == []
