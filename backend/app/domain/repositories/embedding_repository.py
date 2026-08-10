from abc import ABC, abstractmethod


class EmbeddingRepository(ABC):
    @abstractmethod
    async def bulk_create(
        self, *, chunk_ids: list[str], vectors: list[list[float]], model_name: str
    ) -> None: ...

    @abstractmethod
    async def search(
        self,
        *,
        subject_id: str,
        query_vector: list[float],
        top_k: int,
        model_name: str,
        document_id: str | None = None,
    ) -> list[tuple[str, float]]:
        """Nearest-neighbour search (cosine distance — lower is more similar)
        over embeddings belonging to the given subject, filtered to a single
        embedding model so a subject that's been re-embedded under a new
        model doesn't mix incompatible vector spaces. Returns (chunk_id,
        distance) pairs, closest first.

        When document_id is given, results are further narrowed to that one
        document — used when a student asks the coach about a specific
        upload rather than the whole subject."""
        ...
