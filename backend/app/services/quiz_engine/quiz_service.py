"""Orchestrates quiz generation, attempts, and grading — the
persistence/ownership layer around the pure grading.py functions and the
LLM-based generator.py. Exams (services/exam_engine/exam_service.py) reuse
this service directly rather than duplicating attempt/grading logic, since an
exam is just a Quiz row with kind='exam' (see docs/ARCHITECTURE.md section 3).
"""
import uuid
from datetime import datetime, timezone

from app.core.exceptions import (
    DocumentNotFoundError,
    QuizAttemptAlreadySubmittedError,
    QuizAttemptNotFoundError,
    QuizNotFoundError,
    QuizQuestionNotFoundError,
)
from app.domain.entities.quiz import QUESTION_TYPES, Quiz, QuizAttempt, QuizQuestion, StudentAnswer
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.concept_repository import ConceptRepository
from app.domain.repositories.quiz_attempt_repository import QuizAttemptRepository
from app.domain.repositories.quiz_repository import QuizRepository
from app.domain.repositories.student_answer_repository import StudentAnswerRepository
from app.services.document_service import DocumentService
from app.services.knowledge_base.document_source import build_document_source_text
from app.services.llm.base import LLMProvider
from app.services.quiz_engine.generator import generate_quiz_questions
from app.services.quiz_engine.grading import grade_objective, grade_open_ended
from app.services.subject_service import SubjectService


class QuizService:
    def __init__(
        self,
        *,
        quiz_repo: QuizRepository,
        attempt_repo: QuizAttemptRepository,
        answer_repo: StudentAnswerRepository,
        document_service: DocumentService,
        subject_service: SubjectService,
        chunk_repo: ChunkRepository,
        concept_repo: ConceptRepository,
        llm_provider: LLMProvider,
        max_source_chars: int,
        default_generate_count: int,
        max_generate_count: int,
    ):
        self._quizzes = quiz_repo
        self._attempts = attempt_repo
        self._answers = answer_repo
        self._documents = document_service
        self._subjects = subject_service
        self._chunks = chunk_repo
        self._concepts = concept_repo
        self._llm = llm_provider
        self._max_source_chars = max_source_chars
        self._default_generate_count = default_generate_count
        self._max_generate_count = max_generate_count

    async def generate(
        self,
        *,
        user_id: str,
        subject_id: str,
        document_id: str,
        count: int | None = None,
        difficulty: str = "medium",
        question_types: list[str] | None = None,
        kind: str = "quiz",
        duration_minutes: int | None = None,
        style: str | None = None,
        title: str | None = None,
    ) -> Quiz:
        document = await self._documents.get_owned(user_id, document_id)
        if document.subject_id != subject_id:
            raise DocumentNotFoundError(document_id)

        resolved_count = min(count or self._default_generate_count, self._max_generate_count)
        types = question_types or list(QUESTION_TYPES)
        source_text = await build_document_source_text(self._chunks, document, self._max_source_chars)
        concepts = await self._concepts.list_by_document(document_id)

        drafts = await generate_quiz_questions(
            llm_provider=self._llm,
            document_filename=document.original_filename,
            source_text=source_text,
            concepts=concepts,
            count=resolved_count,
            question_types=types,
            difficulty=difficulty,
        )

        used_concept_ids = {d.concept_id for d in drafts if d.concept_id}
        topics = [c.name for c in concepts if c.id in used_concept_ids]

        quiz = await self._quizzes.create(
            subject_id=subject_id,
            user_id=user_id,
            title=title or f"{document.original_filename} — {kind}",
            kind=kind,
            difficulty=difficulty,
            topics=topics,
            duration_minutes=duration_minutes,
            style=style,
        )
        if drafts:
            await self._quizzes.bulk_create_questions(quiz_id=quiz.id, drafts=drafts)
        return quiz

    async def get_owned(self, *, user_id: str, quiz_id: str) -> Quiz:
        quiz = await self._quizzes.get_by_id(quiz_id)
        if quiz is None:
            raise QuizNotFoundError(quiz_id)
        await self._subjects.get_owned(user_id, quiz.subject_id)  # 404s if this user doesn't own the subject
        return quiz

    async def get_questions(self, quiz_id: str) -> list[QuizQuestion]:
        return await self._quizzes.list_questions(quiz_id)

    async def start_attempt(self, *, user_id: str, quiz_id: str) -> QuizAttempt:
        await self.get_owned(user_id=user_id, quiz_id=quiz_id)
        return await self._attempts.create(quiz_id=quiz_id, user_id=user_id)

    async def submit_answer(
        self,
        *,
        user_id: str,
        attempt_id: str,
        question_id: str,
        answer: str,
        time_spent_seconds: int | None = None,
    ) -> StudentAnswer:
        attempt = await self._get_owned_attempt(user_id, attempt_id)
        if attempt.completed_at is not None:
            raise QuizAttemptAlreadySubmittedError(attempt_id)

        question = await self._quizzes.get_question_by_id(question_id)
        if question is None or question.quiz_id != attempt.quiz_id:
            raise QuizQuestionNotFoundError(question_id)

        is_correct = grade_objective(question, answer)
        if is_correct is None:
            is_correct = await grade_open_ended(llm_provider=self._llm, question=question, answer=answer)

        return await self._answers.upsert(
            quiz_attempt_id=attempt.id,
            quiz_question_id=question_id,
            answer=answer,
            is_correct=is_correct,
            time_spent_seconds=time_spent_seconds,
            submitted_at=datetime.now(timezone.utc),
        )

    async def submit_attempt(
        self, *, user_id: str, attempt_id: str
    ) -> tuple[QuizAttempt, list[QuizQuestion], list[StudentAnswer]]:
        attempt = await self._get_owned_attempt(user_id, attempt_id)
        if attempt.completed_at is not None:
            raise QuizAttemptAlreadySubmittedError(attempt_id)

        questions = await self._quizzes.list_questions(attempt.quiz_id)
        answers = await self._answers.list_by_attempt(attempt.id)
        answers_by_question = {a.quiz_question_id: a for a in answers}

        total_points = sum(q.points for q in questions) or 1
        earned_points = sum(
            q.points for q in questions
            if (a := answers_by_question.get(q.id)) is not None and a.is_correct
        )
        score = round(100 * earned_points / total_points, 2)

        completed = await self._attempts.complete(attempt.id, completed_at=datetime.now(timezone.utc), score=score)
        return completed, questions, answers

    async def get_attempt_with_results(
        self, *, user_id: str, attempt_id: str
    ) -> tuple[QuizAttempt, list[QuizQuestion], list[StudentAnswer]]:
        attempt = await self._get_owned_attempt(user_id, attempt_id)
        questions = await self._quizzes.list_questions(attempt.quiz_id)
        answers = await self._answers.list_by_attempt(attempt.id)
        return attempt, questions, answers

    async def _get_owned_attempt(self, user_id: str, attempt_id: str) -> QuizAttempt:
        attempt = await self._attempts.get_by_id(attempt_id)
        if attempt is None or attempt.user_id != user_id:
            raise QuizAttemptNotFoundError(attempt_id)
        return attempt
