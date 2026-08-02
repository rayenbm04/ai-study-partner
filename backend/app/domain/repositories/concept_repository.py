from abc import ABC, abstractmethod

from app.domain.entities.concept import Concept


class ConceptRepository(ABC):
    @abstractmethod
    async def list_by_subject(self, subject_id: str) -> list[Concept]: ...

    @abstractmethod
    async def get_by_subject_and_name(self, subject_id: str, name: str) -> Concept | None: ...

    @abstractmethod
    async def create(self, *, subject_id: str, name: str, description: str | None) -> Concept: ...

    @abstractmethod
    async def add_prerequisite(self, *, concept_id: str, prerequisite_id: str) -> None: ...

    @abstractmethod
    async def list_by_document(self, document_id: str) -> list[Concept]:
        """Concepts tagged to any chunk belonging to this document (via
        concept_chunks) — used by the summary engine to ground the
        'key concepts' summary type in the real per-subject concept graph
        instead of asking the LLM to invent concept names from scratch."""
        ...
