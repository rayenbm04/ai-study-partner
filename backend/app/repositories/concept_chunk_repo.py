from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.concept_chunk_repository import ConceptChunkRepository
from app.infrastructure.db.models.concept_chunk import ConceptChunkModel


class SqlAlchemyConceptChunkRepository(ConceptChunkRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def link(self, *, concept_id: str, chunk_id: str, relevance: float) -> None:
        self._session.add(ConceptChunkModel(concept_id=concept_id, chunk_id=chunk_id, relevance=relevance))
        await self._session.flush()
