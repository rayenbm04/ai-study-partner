from abc import ABC, abstractmethod

from app.domain.entities.chunk import Chunk, ChunkDraft


class ChunkRepository(ABC):
    @abstractmethod
    async def bulk_create(self, *, document_id: str, subject_id: str, drafts: list[ChunkDraft]) -> list[Chunk]:
        """Persists parent chunks first, then children with parent_chunk_id
        resolved from ChunkDraft.parent_index, and returns all of them in the
        same order as `drafts`."""
        ...

    @abstractmethod
    async def list_by_document(self, document_id: str) -> list[Chunk]: ...

    @abstractmethod
    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        """Used by retrieval: fetch metadata (page/section/parent) for chunks
        that came back from a vector search, and to resolve each retrieved
        child chunk's parent for fuller context assembly."""
        ...
