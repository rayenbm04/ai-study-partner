from datetime import datetime, timezone

import pytest

from app.core.exceptions import SubjectNotFoundError
from app.domain.entities.flashcard import FlashcardDraft
from app.domain.entities.quiz import QuizQuestionDraft
from app.services.analytics_engine.analytics_service import AnalyticsService
from app.services.document_service import DocumentService
from app.services.flashcard_engine.flashcard_service import FlashcardService
from app.services.progress_engine.progress_service import ProgressService
from app.services.subject_service import SubjectService
from tests.unit.fakes import (
    FakeChunkRepository,
    FakeConceptRepository,
    FakeConversationRepository,
    FakeDocumentRepository,
    FakeFlashcardRepository,
    FakeFlashcardReviewRepository,
    FakeLLMProvider,
    FakeProgressRepository,
    FakeQuizAttemptRepository,
    FakeQuizRepository,
    FakeStorage,
    FakeStudentAnswerRepository,
    FakeSubjectRepository,
    FakeWeakConceptRepository,
)


async def _build():
    subject_repo = FakeSubjectRepository()
    subject_service = SubjectService(subject_repo)
    document_repo = FakeDocumentRepository()
    concept_repo = FakeConceptRepository()
    flashcard_repo = FakeFlashcardRepository(subject_repo=subject_repo)
    flashcard_review_repo = FakeFlashcardReviewRepository()
    quiz_repo = FakeQuizRepository()
    quiz_attempt_repo = FakeQuizAttemptRepository()
    student_answer_repo = FakeStudentAnswerRepository()
    conversation_repo = FakeConversationRepository()

    document_service = DocumentService(
        document_repo=document_repo, subject_service=subject_service, storage=FakeStorage(), max_upload_bytes=1_000_000
    )

    flashcard_service = FlashcardService(
        flashcard_repo=flashcard_repo,
        review_repo=flashcard_review_repo,
        document_service=document_service,
        subject_service=subject_service,
        chunk_repo=FakeChunkRepository(),
        concept_repo=concept_repo,
        llm_provider=FakeLLMProvider(),
        max_source_chars=10_000,
        default_generate_count=5,
        max_generate_count=20,
    )
    progress_service = ProgressService(
        subject_service=subject_service,
        concept_repo=concept_repo,
        flashcard_repo=flashcard_repo,
        flashcard_review_repo=flashcard_review_repo,
        quiz_repo=quiz_repo,
        quiz_attempt_repo=quiz_attempt_repo,
        student_answer_repo=student_answer_repo,
        progress_repo=FakeProgressRepository(),
        weak_concept_repo=FakeWeakConceptRepository(),
    )
    service = AnalyticsService(
        document_repo=document_repo,
        quiz_repo=quiz_repo,
        quiz_attempt_repo=quiz_attempt_repo,
        conversation_repo=conversation_repo,
        flashcard_service=flashcard_service,
        subject_service=subject_service,
        progress_service=progress_service,
    )
    repos = {
        "subject_repo": subject_repo,
        "document_repo": document_repo,
        "concept_repo": concept_repo,
        "flashcard_repo": flashcard_repo,
        "flashcard_review_repo": flashcard_review_repo,
        "quiz_repo": quiz_repo,
        "quiz_attempt_repo": quiz_attempt_repo,
        "student_answer_repo": student_answer_repo,
        "conversation_repo": conversation_repo,
    }
    return service, repos


async def test_get_subject_analytics_raises_when_not_owned():
    service, repos = await _build()
    subject = await repos["subject_repo"].create(
        user_id="user-1", name="Physics", description=None, color=None, icon=None
    )

    with pytest.raises(SubjectNotFoundError):
        await service.get_subject_analytics(user_id="someone-else", subject_id=subject.id)


async def test_get_subject_analytics_on_empty_subject_returns_zeros():
    service, repos = await _build()
    subject = await repos["subject_repo"].create(
        user_id="user-1", name="Physics", description=None, color=None, icon=None
    )

    analytics = await service.get_subject_analytics(user_id="user-1", subject_id=subject.id)

    assert analytics.subject_name == "Physics"
    assert analytics.document_count == 0
    assert analytics.flashcard_count == 0
    assert analytics.flashcards_due_count == 0
    assert analytics.quiz_count == 0
    assert analytics.exam_count == 0
    assert analytics.quiz_attempt_count == 0
    assert analytics.average_quiz_score is None
    assert analytics.conversation_count == 0
    assert analytics.average_mastery is None
    assert analytics.weak_concept_count == 0
    assert analytics.concepts_practiced == 0
    assert analytics.concepts_total == 0


async def test_get_subject_analytics_counts_flashcards_and_due_cards():
    service, repos = await _build()
    subject = await repos["subject_repo"].create(
        user_id="user-1", name="Physics", description=None, color=None, icon=None
    )
    await repos["flashcard_repo"].bulk_create(
        subject_id=subject.id,
        drafts=[
            FlashcardDraft(question="q1", answer="a1", difficulty="easy", tags=[], concept_id=None, source="generated"),
            FlashcardDraft(question="q2", answer="a2", difficulty="easy", tags=[], concept_id=None, source="generated"),
        ],
    )

    analytics = await service.get_subject_analytics(user_id="user-1", subject_id=subject.id)

    assert analytics.flashcard_count == 2
    assert analytics.flashcards_due_count == 2  # never reviewed -> both due


async def test_get_subject_analytics_computes_average_quiz_score_and_kind_counts():
    service, repos = await _build()
    subject = await repos["subject_repo"].create(
        user_id="user-1", name="Physics", description=None, color=None, icon=None
    )
    quiz = await repos["quiz_repo"].create(
        subject_id=subject.id, user_id="user-1", title="Quiz", kind="quiz", difficulty="easy",
        topics=[], duration_minutes=None, style=None,
    )
    exam = await repos["quiz_repo"].create(
        subject_id=subject.id, user_id="user-1", title="Exam", kind="exam", difficulty="hard",
        topics=[], duration_minutes=60, style=None,
    )
    attempt1 = await repos["quiz_attempt_repo"].create(quiz_id=quiz.id, user_id="user-1")
    await repos["quiz_attempt_repo"].complete(attempt1.id, completed_at=datetime.now(timezone.utc), score=80.0)
    attempt2 = await repos["quiz_attempt_repo"].create(quiz_id=exam.id, user_id="user-1")
    await repos["quiz_attempt_repo"].complete(attempt2.id, completed_at=datetime.now(timezone.utc), score=60.0)

    analytics = await service.get_subject_analytics(user_id="user-1", subject_id=subject.id)

    assert analytics.quiz_count == 1
    assert analytics.exam_count == 1
    assert analytics.quiz_attempt_count == 2
    assert analytics.average_quiz_score == 70.0


async def test_get_subject_analytics_computes_average_mastery_and_weak_count():
    service, repos = await _build()
    subject = await repos["subject_repo"].create(
        user_id="user-1", name="Physics", description=None, color=None, icon=None
    )
    concept = await repos["concept_repo"].create(subject_id=subject.id, name="Ohm's Law", description=None)
    quiz = await repos["quiz_repo"].create(
        subject_id=subject.id, user_id="user-1", title="Quiz", kind="quiz", difficulty="easy",
        topics=[], duration_minutes=None, style=None,
    )
    questions = await repos["quiz_repo"].bulk_create_questions(
        quiz_id=quiz.id,
        drafts=[
            QuizQuestionDraft(
                type="mcq", question=f"q{i}", options=["a", "b"], correct_answer="a", explanation=None,
                points=1, difficulty="easy", concept_id=concept.id,
            )
            for i in range(3)
        ],
    )
    attempt = await repos["quiz_attempt_repo"].create(quiz_id=quiz.id, user_id="user-1")
    now = datetime.now(timezone.utc)
    for i, question in enumerate(questions):
        await repos["student_answer_repo"].upsert(
            quiz_attempt_id=attempt.id, quiz_question_id=question.id, answer="b",
            is_correct=(i == 2), time_spent_seconds=5, submitted_at=now,
        )

    analytics = await service.get_subject_analytics(user_id="user-1", subject_id=subject.id)

    assert analytics.concepts_total == 1
    assert analytics.concepts_practiced == 1
    assert analytics.average_mastery == pytest.approx(33.3, abs=0.1)
    assert analytics.weak_concept_count == 1  # 2/3 wrong -> above default error rate threshold


async def test_get_overview_aggregates_across_subjects():
    service, repos = await _build()
    subject1 = await repos["subject_repo"].create(
        user_id="user-1", name="Physics", description=None, color=None, icon=None
    )
    subject2 = await repos["subject_repo"].create(
        user_id="user-1", name="Chemistry", description=None, color=None, icon=None
    )
    await repos["flashcard_repo"].bulk_create(
        subject_id=subject1.id,
        drafts=[FlashcardDraft(question="q", answer="a", difficulty="easy", tags=[], concept_id=None, source="generated")],
    )
    await repos["flashcard_repo"].bulk_create(
        subject_id=subject2.id,
        drafts=[
            FlashcardDraft(question="q1", answer="a1", difficulty="easy", tags=[], concept_id=None, source="generated"),
            FlashcardDraft(question="q2", answer="a2", difficulty="easy", tags=[], concept_id=None, source="generated"),
        ],
    )

    overview = await service.get_overview(user_id="user-1")

    assert overview.subject_count == 2
    assert overview.total_flashcards_due == 3
    assert {s.subject_id for s in overview.subjects} == {subject1.id, subject2.id}
