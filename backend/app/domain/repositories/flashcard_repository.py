from abc import ABC, abstractmethod

from app.domain.entities.flashcard import Flashcard, FlashcardDraft


class FlashcardRepository(ABC):
    @abstractmethod
    async def bulk_create(self, *, subject_id: str, drafts: list[FlashcardDraft]) -> list[Flashcard]: ...

    @abstractmethod
    async def get_by_id(self, flashcard_id: str) -> Flashcard | None: ...

    @abstractmethod
    async def list_by_subject(self, subject_id: str) -> list[Flashcard]: ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Flashcard]:
        """Every flashcard across every subject this user owns — joins
        through subjects, since flashcards don't carry user_id directly (they
        belong to a subject, which belongs to a user). Used by the global
        GET /flashcards/due endpoint, which isn't subject-scoped."""
        ...
