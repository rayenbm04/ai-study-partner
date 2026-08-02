from abc import ABC, abstractmethod


class EmbeddingRepository(ABC):
    @abstractmethod
    async def bulk_create(
        self, *, chunk_ids: list[str], vectors: list[list[float]], model_name: str
    ) -> None: ...
