from abc import ABC, abstractmethod

from app.domain.entities.progress import WeakConcept


class WeakConceptRepository(ABC):
    @abstractmethod
    async def create(self, *, user_id: str, concept_id: str, reason: str, confidence: float) -> WeakConcept:
        """Always creates a new row with status='active' — callers check
        get_active_by_user_and_concept() first so a concept doesn't
        accumulate multiple simultaneous active flags (see
        update_active())."""
        ...

    @abstractmethod
    async def update_active(self, weak_concept_id: str, *, reason: str, confidence: float) -> WeakConcept:
        """Refreshes an already-active detection's reason/confidence/
        detected_at, rather than creating a duplicate row for the same
        ongoing gap."""
        ...

    @abstractmethod
    async def resolve(self, weak_concept_id: str) -> WeakConcept:
        """Marks a detection resolved once the concept's mastery recovers —
        it stays in history rather than being deleted."""
        ...

    @abstractmethod
    async def get_active_by_user_and_concept(self, user_id: str, concept_id: str) -> WeakConcept | None: ...

    @abstractmethod
    async def list_active_by_user(self, user_id: str) -> list[WeakConcept]:
        """Every currently-active weak concept across every subject this
        user owns — the service filters this down to one subject's concepts,
        same pattern as ProgressRepository.list_by_user."""
        ...
