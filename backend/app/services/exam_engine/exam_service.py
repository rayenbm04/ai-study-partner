"""Exams are quizzes with kind='exam' — same generation, attempt, and grading
machinery as a regular quiz (docs/ARCHITECTURE.md section 3: "quizzes.kind
distinguishes quiz vs. exam instead of duplicating tables"). This service is
a thin wrapper around QuizService adding the two things that are genuinely
exam-specific: generation params (duration_minutes, style) and a
per-exam history view. Everything else — GET /quizzes/{id}, starting an
attempt, submitting answers, finalizing an attempt — goes through the exact
same QuizService methods and routes an ordinary quiz would, since an exam's
id IS a quiz id.
"""
from app.core.exceptions import QuizNotFoundError
from app.domain.entities.quiz import Quiz, QuizAttempt
from app.domain.repositories.quiz_attempt_repository import QuizAttemptRepository
from app.services.quiz_engine.quiz_service import QuizService


class ExamService:
    def __init__(self, *, quiz_service: QuizService, attempt_repo: QuizAttemptRepository):
        self._quizzes = quiz_service
        self._attempts = attempt_repo

    async def generate(
        self,
        *,
        user_id: str,
        subject_id: str,
        document_id: str,
        count: int | None = None,
        difficulty: str = "medium",
        question_types: list[str] | None = None,
        duration_minutes: int | None = None,
        style: str | None = None,
        title: str | None = None,
    ) -> Quiz:
        return await self._quizzes.generate(
            user_id=user_id,
            subject_id=subject_id,
            document_id=document_id,
            count=count,
            difficulty=difficulty,
            question_types=question_types,
            kind="exam",
            duration_minutes=duration_minutes,
            style=style,
            title=title,
        )

    async def get_history(self, *, user_id: str, exam_id: str) -> list[QuizAttempt]:
        exam = await self._quizzes.get_owned(user_id=user_id, quiz_id=exam_id)
        if exam.kind != "exam":
            raise QuizNotFoundError(exam_id)
        attempts = await self._attempts.list_by_quiz(exam_id)
        return [a for a in attempts if a.user_id == user_id]
