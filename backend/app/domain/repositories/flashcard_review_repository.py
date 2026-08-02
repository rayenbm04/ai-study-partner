from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.flashcard import FlashcardReview


class FlashcardReviewRepository(ABC):
    @abstractmethod
    async def upsert(
        self,
        *,
        flashcard_id: str,
        user_id: str,
        ease_factor: float,
        interval_days: int,
        repetitions: int,
        last_grade: int,
        last_reviewed_at: datetime,
        next_review_date: datetime,
    ) -> FlashcardReview:
        """One row per (flashcard_id, user_id) — a review updates this
        student's SM-2 state for this card in place rather than logging every
        past review as a separate row."""
        ...

    @abstractmethod
    async def get_by_flashcard_and_user(self, flashcard_id: str, user_id: str) -> FlashcardReview | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[FlashcardReview]: ...
