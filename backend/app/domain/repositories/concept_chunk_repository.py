from abc import ABC, abstractmethod


class ConceptChunkRepository(ABC):
    @abstractmethod
    async def link(self, *, concept_id: str, chunk_id: str, relevance: float) -> None: ...
