from abc import ABC, abstractmethod

from app.domain.entities.summary import Summary


class SummaryRepository(ABC):
    @abstractmethod
    async def upsert(self, *, document_id: str, subject_id: str, summary_type: str, content: str) -> Summary:
        """One summary per (document_id, summary_type) — generating the same
        type again overwrites the previous content rather than accumulating
        history, since a summary is a cache of "what does this document say",
        not a log of past generations."""
        ...

    @abstractmethod
    async def get_by_document_and_type(self, document_id: str, summary_type: str) -> Summary | None: ...

    @abstractmethod
    async def list_by_document(self, document_id: str) -> list[Summary]: ...
