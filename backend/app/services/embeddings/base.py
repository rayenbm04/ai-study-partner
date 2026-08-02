from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds chunk content for storage/retrieval."""
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embeds a search query. Kept distinct from embed_documents because
        Gemini (and most modern embedding APIs) use a different task-type
        internally for queries vs. documents, which measurably improves
        retrieval quality — used starting Phase 4's RAG chat."""
        ...
