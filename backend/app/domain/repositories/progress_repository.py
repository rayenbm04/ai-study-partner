from abc import ABC, abstractmethod

from app.domain.entities.progress import Progress


class ProgressRepository(ABC):
    @abstractmethod
    async def upsert(self, *, user_id: str, concept_id: str, mastery_score: float, trend: str) -> Progress:
        """One row per (user_id, concept_id) — a recompute updates this
        student's mastery for this concept in place rather than logging every
        past score, matching the same one-row-per-pair shape as
        FlashcardReview."""
        ...

    @abstractmethod
    async def get_by_user_and_concept(self, user_id: str, concept_id: str) -> Progress | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Progress]:
        """Every concept this user has a mastery score for, across every
        subject — the service filters this down to one subject's concepts
        (mirrors the FlashcardReviewRepository.list_by_user pattern)."""
        ...
