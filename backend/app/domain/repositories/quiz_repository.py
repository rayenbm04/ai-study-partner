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
    async def list_questions(self, quiz_id: str) -> list[QuizQuestion]: ...

    @abstractmethod
    async def get_question_by_id(self, question_id: str) -> QuizQuestion | None: ...
