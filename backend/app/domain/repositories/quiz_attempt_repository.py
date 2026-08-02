from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.quiz import QuizAttempt


class QuizAttemptRepository(ABC):
    @abstractmethod
    async def create(self, *, quiz_id: str, user_id: str) -> QuizAttempt: ...

    @abstractmethod
    async def get_by_id(self, attempt_id: str) -> QuizAttempt | None: ...

    @abstractmethod
    async def list_by_quiz(self, quiz_id: str) -> list[QuizAttempt]:
        """Every attempt made against this quiz, across all students who
        attempted it — used by exam history, filtered down to one user's own
        attempts by the caller (a student's history shouldn't leak classmates'
        scores, even though the schema doesn't block cross-user sharing in
        general — see docs/ARCHITECTURE.md section 3)."""
        ...

    @abstractmethod
    async def complete(self, attempt_id: str, *, completed_at: datetime, score: float) -> QuizAttempt: ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[QuizAttempt]:
        """Every attempt this user has ever made, across every quiz/subject —
        used by the progress engine to gather quiz/exam evidence; the service
        filters down to attempts on quizzes belonging to one subject (same
        list-then-filter pattern as FlashcardReviewRepository.list_by_user)."""
        ...
