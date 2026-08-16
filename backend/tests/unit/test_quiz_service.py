import json

import pytest

from app.core.exceptions import (
    DocumentNotFoundError,
    QuizAttemptAlreadySubmittedError,
    QuizAttemptNotFoundError,
    QuizNotFoundError,
    QuizQuestionNotFoundError,
    SubjectNotFoundError,
)
from app.domain.entities.chunk import ChunkDraft
from app.services.document_service import DocumentService
from app.services.quiz_engine.quiz_service import QuizService
from app.services.subject_service import SubjectService
from tests.unit.fakes import (
    FakeChunkRepository,
    FakeConceptChunkRepository,
    FakeConceptRepository,
    FakeDocumentRepository,
    FakeLLMProvider,
    FakeQuizAttemptRepository,
    FakeQuizRepository,
    FakeStorage,
    FakeStudentAnswerRepository,
    FakeSubjectRepository,
)


async def _build(*, llm, default_count=10, max_count=30):
    subject_repo = FakeSubjectRepository()
    subject_service = SubjectService(subject_repo)
    document_repo = FakeDocumentRepository()
    document_service = DocumentService(
        document_repo=document_repo, subject_service=subject_service, storage=FakeStorage(),
        max_upload_bytes=50 * 1024 * 1024,
    )
    chunk_repo = FakeChunkRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    concept_repo = FakeConceptRepository(concept_chunk_repo=concept_chunk_repo, chunk_repo=chunk_repo)
    quiz_repo = FakeQuizRepository()
    attempt_repo = FakeQuizAttemptRepository()
    answer_repo = FakeStudentAnswerRepository()

    service = QuizService(
        quiz_repo=quiz_repo, attempt_repo=attempt_repo, answer_repo=answer_repo,
        document_service=document_service, subject_service=subject_service, chunk_repo=chunk_repo,
        concept_repo=concept_repo, llm_provider=llm, max_source_chars=16000,
        default_generate_count=default_count, max_generate_count=max_count,
    )
    return service, subject_repo, document_repo, chunk_repo, quiz_repo, attempt_repo, answer_repo


async def _seed_ready_document(subject_repo, document_repo, chunk_repo, *, user_id="user-1"):
    subject = await subject_repo.create(user_id=user_id, name="Physics", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="notes.pdf",
        storage_path="x", file_type=".pdf",
    )
    drafts = [
        ChunkDraft(
            content="Ohm's law relates voltage, current, and resistance.", chunk_type="parent",
            parent_index=None, page=1, section_title=None, chapter=None, token_count=10,
        )
    ]
    await chunk_repo.bulk_create(document_id=document.id, subject_id=subject.id, drafts=drafts)
    await document_repo.mark_ready(document.id, page_count=1)
    document = await document_repo.get_by_id(document.id)
    return subject, document


_TWO_MCQ_RESPONSE = json.dumps(
    {
        "questions": [
            {"type": "mcq", "question": "V = ?", "options": ["I*R", "I+R"], "correct_answer": "I*R",
             "explanation": "Ohm's law", "points": 1, "difficulty": "easy", "concept_name": None},
            {"type": "mcq", "question": "Unit of resistance?", "options": ["Ohm", "Volt"], "correct_answer": "Ohm",
             "explanation": "Resistance is in ohms", "points": 1, "difficulty": "easy", "concept_name": None},
        ]
    }
)

_ONE_SHORT_ANSWER_RESPONSE = json.dumps(
    {
        "questions": [
            {"type": "short_answer", "question": "State Ohm's law.", "options": None,
             "correct_answer": "V = I * R", "explanation": "...", "points": 3, "difficulty": "medium",
             "concept_name": None},
        ]
    }
)


async def test_generate_creates_quiz_and_persists_questions():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, quiz_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    assert quiz.kind == "quiz"
    questions = await quiz_repo.list_questions(quiz.id)
    assert len(questions) == 2


async def test_list_for_subject_returns_generated_quizzes():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, quiz_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id, kind="exam")

    quizzes = await service.list_for_subject(user_id="user-1", subject_id=subject.id)

    assert {q.kind for q in quizzes} == {"quiz", "exam"}


async def test_list_for_subject_raises_when_not_owned():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response=_TWO_MCQ_RESPONSE))
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo, user_id="user-1")

    with pytest.raises(SubjectNotFoundError):
        await service.list_for_subject(user_id="someone-else", subject_id=subject.id)


async def test_generate_raises_when_document_belongs_to_different_subject():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    other_subject = await subject_repo.create(user_id="user-1", name="Chemistry", description=None, color=None, icon=None)

    with pytest.raises(DocumentNotFoundError):
        await service.generate(user_id="user-1", subject_id=other_subject.id, document_id=document.id)


async def test_get_owned_raises_for_unknown_quiz():
    service, *_ = await _build(llm=FakeLLMProvider(response="{}"))

    with pytest.raises(QuizNotFoundError):
        await service.get_owned(user_id="user-1", quiz_id="does-not-exist")


async def test_start_attempt_creates_attempt_for_owned_quiz():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)

    assert attempt.quiz_id == quiz.id
    assert attempt.user_id == "user-1"
    assert attempt.completed_at is None
    assert attempt.score is None


async def test_submit_answer_grades_mcq_without_llm_call():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, quiz_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    questions = await quiz_repo.list_questions(quiz.id)
    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)
    calls_before = len(llm.calls)

    answer = await service.submit_answer(
        user_id="user-1", attempt_id=attempt.id, question_id=questions[0].id, answer=questions[0].correct_answer,
    )

    assert answer.is_correct is True
    assert len(llm.calls) == calls_before  # no extra LLM call for auto-gradable types


async def test_submit_answer_grades_open_ended_via_llm():
    llm = FakeLLMProvider(responses=[_ONE_SHORT_ANSWER_RESPONSE, json.dumps({"is_correct": True})])
    service, subject_repo, document_repo, chunk_repo, quiz_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    questions = await quiz_repo.list_questions(quiz.id)
    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)

    answer = await service.submit_answer(
        user_id="user-1", attempt_id=attempt.id, question_id=questions[0].id, answer="voltage is current times resistance",
    )

    assert answer.is_correct is True


async def test_submit_answer_raises_for_question_not_in_quiz():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)

    with pytest.raises(QuizQuestionNotFoundError):
        await service.submit_answer(
            user_id="user-1", attempt_id=attempt.id, question_id="does-not-exist", answer="x",
        )


async def test_submit_answer_raises_after_attempt_already_submitted():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, quiz_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    questions = await quiz_repo.list_questions(quiz.id)
    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)
    await service.submit_attempt(user_id="user-1", attempt_id=attempt.id)

    with pytest.raises(QuizAttemptAlreadySubmittedError):
        await service.submit_answer(
            user_id="user-1", attempt_id=attempt.id, question_id=questions[0].id, answer="x",
        )


async def test_submit_attempt_computes_score_from_correct_answers():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, quiz_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    questions = await quiz_repo.list_questions(quiz.id)
    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)

    await service.submit_answer(
        user_id="user-1", attempt_id=attempt.id, question_id=questions[0].id, answer=questions[0].correct_answer,
    )
    await service.submit_answer(
        user_id="user-1", attempt_id=attempt.id, question_id=questions[1].id, answer="wrong answer",
    )

    completed, result_questions, answers = await service.submit_attempt(user_id="user-1", attempt_id=attempt.id)

    assert completed.completed_at is not None
    assert completed.score == 50.0
    assert len(result_questions) == 2
    assert len(answers) == 2


async def test_submit_attempt_raises_when_already_submitted():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)
    await service.submit_attempt(user_id="user-1", attempt_id=attempt.id)

    with pytest.raises(QuizAttemptAlreadySubmittedError):
        await service.submit_attempt(user_id="user-1", attempt_id=attempt.id)


async def test_attempt_ownership_is_isolated_between_users():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)
    attempt = await service.start_attempt(user_id="user-1", quiz_id=quiz.id)

    with pytest.raises(QuizAttemptNotFoundError):
        await service.submit_attempt(user_id="someone-else", attempt_id=attempt.id)


async def test_generate_respects_max_generate_count_cap():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm, max_count=1)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id, count=50)

    assert "1" in llm.calls[0]["system"]


async def test_delete_removes_quiz_and_its_questions():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, quiz_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    await service.delete(user_id="user-1", quiz_id=quiz.id)

    assert await quiz_repo.get_by_id(quiz.id) is None
    assert await quiz_repo.list_questions(quiz.id) == []


async def test_delete_raises_when_not_owned():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    with pytest.raises(SubjectNotFoundError):
        await service.delete(user_id="someone-else", quiz_id=quiz.id)


async def test_delete_raises_for_unknown_quiz():
    service, *_ = await _build(llm=FakeLLMProvider(response="{}"))

    with pytest.raises(QuizNotFoundError):
        await service.delete(user_id="user-1", quiz_id="nonexistent")
