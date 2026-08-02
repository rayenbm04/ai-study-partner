from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.infrastructure.db.models.embedding import EmbeddingModel


class SqlAlchemyEmbeddingRepository(EmbeddingRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def bulk_create(self, *, chunk_ids: list[str], vectors: list[list[float]], model_name: str) -> None:
        if len(chunk_ids) != len(vectors):
            raise ValueError(f"Got {len(chunk_ids)} chunk ids but {len(vectors)} vectors.")
        for chunk_id, vector in zip(chunk_ids, vectors):
            self._session.add(EmbeddingModel(chunk_id=chunk_id, model_name=model_name, vector=vector))
        await self._session.flush()
