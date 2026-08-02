"""Orchestrates one document from stored bytes to a fully populated,
searchable, concept-tagged set of chunks: extract -> chunk -> embed -> tag.

Deliberately has no exception handling of its own — status transitions on
failure are the caller's job (see ingestion_task.py), so this class stays a
straightforward, fully unit-testable sequence of steps against fakes.
"""
import logging

from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.concept_chunk_repository import ConceptChunkRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.infrastructure.storage.base import StoragePort
from app.services.embeddings.base import EmbeddingProvider
from app.services.knowledge_base.chunking import chunk_segments
from app.services.knowledge_base.concept_tagger import ConceptTagger
from app.services.knowledge_base.extractors.registry import get_extractor

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        concept_chunk_repo: ConceptChunkRepository,
        embedding_repo: EmbeddingRepository,
        storage: StoragePort,
        embedding_provider: EmbeddingProvider,
        concept_tagger: ConceptTagger,
        chunk_parent_chars: int,
        chunk_child_chars: int,
        chunk_overlap_chars: int,
    ):
        self._documents = document_repo
        self._chunks = chunk_repo
        self._concept_chunks = concept_chunk_repo
        self._embeddings = embedding_repo
        self._storage = storage
        self._embedder = embedding_provider
        self._concept_tagger = concept_tagger
        self._parent_chars = chunk_parent_chars
        self._child_chars = chunk_child_chars
        self._overlap_chars = chunk_overlap_chars

    async def run(self, document_id: str) -> None:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            logger.warning("Ingestion requested for unknown document %s", document_id)
            return

        await self._documents.mark_processing(document_id)

        content = await self._storage.read(document.storage_path)
        extractor = get_extractor(document.original_filename)
        segments = extractor(content, document.original_filename)

        drafts = chunk_segments(
            segments,
            parent_chars=self._parent_chars,
            child_chars=self._child_chars,
            overlap_chars=self._overlap_chars,
        )
        chunks = await self._chunks.bulk_create(
            document_id=document_id, subject_id=document.subject_id, drafts=drafts
        )

        child_chunks = [chunk for chunk in chunks if chunk.chunk_type == "child"]
        if child_chunks:
            vectors = await self._embedder.embed_documents([chunk.content for chunk in child_chunks])
            await self._embeddings.bulk_create(
                chunk_ids=[chunk.id for chunk in child_chunks],
                vectors=vectors,
                model_name=self._embedder.model_name,
            )

        # Concept tagging runs on parent chunks: coherent, standalone units,
        # rather than the smaller overlapping child chunks used for retrieval.
        parent_chunks = [chunk for chunk in chunks if chunk.chunk_type == "parent"]
        for chunk in parent_chunks:
            await self._concept_tagger.tag_chunk(
                subject_id=document.subject_id, chunk_id=chunk.id, chunk_content=chunk.content
            )

        page_numbers = [segment.page for segment in segments if segment.page is not None]
        page_count = max(page_numbers) if page_numbers else len(segments)
        await self._documents.mark_ready(document_id, page_count=page_count)
