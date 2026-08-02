from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.quiz import StudentAnswer


class StudentAnswerRepository(ABC):
    @abstractmethod
    async def upsert(
        self,
        *,
        quiz_attempt_id: str,
        quiz_question_id: str,
        answer: str,
        is_correct: bool | None,
        time_spent_seconds: int | None,
        submitted_at: datetime,
    ) -> StudentAnswer:
        """One row per (quiz_attempt_id, quiz_question_id) — a student
        resubmitting an answer before the attempt is finalized overwrites the
        prior answer for that question rather than logging every attempt."""
        ...

    @abstractmethod
    async def list_by_attempt(self, quiz_attempt_id: str) -> list[StudentAnswer]: ...
