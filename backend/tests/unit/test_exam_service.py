import json

import pytest

from app.core.exceptions import QuizNotFoundError
from app.domain.entities.chunk import ChunkDraft
from app.services.document_service import DocumentService
from app.services.exam_engine.exam_service import ExamService
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


async def _build(*, llm):
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

    quiz_service = QuizService(
        quiz_repo=quiz_repo, attempt_repo=attempt_repo, answer_repo=answer_repo,
        document_service=document_service, subject_service=subject_service, chunk_repo=chunk_repo,
        concept_repo=concept_repo, llm_provider=llm, max_source_chars=16000,
        default_generate_count=10, max_generate_count=30,
    )
    exam_service = ExamService(quiz_service=quiz_service, attempt_repo=attempt_repo)
    return exam_service, quiz_service, subject_repo, document_repo, chunk_repo


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


async def test_generate_creates_quiz_with_exam_kind_and_params():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    exam_service, quiz_service, subject_repo, document_repo, chunk_repo = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    exam = await exam_service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id,
        duration_minutes=60, style="past-exam",
    )

    assert exam.kind == "exam"
    assert exam.duration_minutes == 60
    assert exam.style == "past-exam"


async def test_get_history_returns_only_this_users_attempts():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    exam_service, quiz_service, subject_repo, document_repo, chunk_repo = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    exam = await exam_service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    attempt1 = await quiz_service.start_attempt(user_id="user-1", quiz_id=exam.id)
    await quiz_service.submit_attempt(user_id="user-1", attempt_id=attempt1.id)

    history = await exam_service.get_history(user_id="user-1", exam_id=exam.id)

    assert len(history) == 1
    assert history[0].id == attempt1.id


async def test_get_history_raises_for_a_quiz_that_is_not_an_exam():
    llm = FakeLLMProvider(response=_TWO_MCQ_RESPONSE)
    exam_service, quiz_service, subject_repo, document_repo, chunk_repo = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    quiz = await quiz_service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)  # kind="quiz"

    with pytest.raises(QuizNotFoundError):
        await exam_service.get_history(user_id="user-1", exam_id=quiz.id)
