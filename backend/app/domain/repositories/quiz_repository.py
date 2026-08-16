from abc import ABC, abstractmethod

from app.domain.entities.quiz import Quiz, QuizQuestion, QuizQuestionDraft


class QuizRepository(ABC):
    @abstractmethod
    async def create(
        self,
        *,
        subject_id: str,
        user_id: str,
        title: str,
        kind: str,
        difficulty: str,
        topics: list[str],
        duration_minutes: int | None,
        style: str | None,
    ) -> Quiz: ...

    @abstractmethod
    async def bulk_create_questions(self, *, quiz_id: str, drafts: list[QuizQuestionDraft]) -> list[QuizQuestion]: ...

    @abstractmethod
    async def get_by_id(self, quiz_id: str) -> Quiz | None: ...

    @abstractmethod
    async def list_by_subject(self, subject_id: str) -> list[Quiz]:
        """Every quiz/exam ever generated for this subject — used by the
        progress engine to find which quiz_ids' answers count as evidence
        for this subject's concepts (quiz_questions don't carry subject_id
        directly, only via quiz_id -> quiz.subject_id)."""
        ...

    @abstractmethod
    async def list_questions(self, quiz_id: str) -> list[QuizQuestion]: ...

    @abstractmethod
    async def get_question_by_id(self, question_id: str) -> QuizQuestion | None: ...

    @abstractmethod
    async def delete(self, quiz_id: str) -> None:
        """Cascades to quiz_questions, quiz_attempts, and student_answers at
        the DB level (all FK'd with ondelete=CASCADE) — nothing else to
        clean up here."""
        ...
