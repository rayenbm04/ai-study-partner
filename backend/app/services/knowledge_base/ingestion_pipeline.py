"""Orchestrates one document from stored bytes to a fully populated,
searchable, concept-tagged set of chunks: extract -> chunk -> embed -> tag.

Deliberately has no exception handling of its own — status transitions on
failure are the caller's job (see ingestion_task.py), so this class stays a
straightforward, fully unit-testable sequence of steps against fakes.
"""
import logging

from app.core.exceptions import ExtractionError
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.concept_chunk_repository import ConceptChunkRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.domain.repositories.subject_repository import SubjectRepository
from app.infrastructure.storage.base import StoragePort
from app.services.embeddings.base import EmbeddingProvider
from app.services.knowledge_base.chunking import chunk_segments
from app.services.knowledge_base.concept_tagger import ConceptTagger
from app.services.knowledge_base.document_classifier import DocumentClassifier
from app.services.knowledge_base.extractors.registry import get_extractor
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        concept_chunk_repo: ConceptChunkRepository,
        embedding_repo: EmbeddingRepository,
        subject_repo: SubjectRepository,
        storage: StoragePort,
        embedding_provider: EmbeddingProvider,
        llm_provider: LLMProvider,
        concept_tagger: ConceptTagger,
        document_classifier: DocumentClassifier,
        chunk_parent_chars: int,
        chunk_child_chars: int,
        chunk_overlap_chars: int,
        classification_max_source_chars: int,
    ):
        self._documents = document_repo
        self._chunks = chunk_repo
        self._concept_chunks = concept_chunk_repo
        self._embeddings = embedding_repo
        self._subjects = subject_repo
        self._storage = storage
        self._embedder = embedding_provider
        self._llm = llm_provider
        self._concept_tagger = concept_tagger
        self._document_classifier = document_classifier
        self._parent_chars = chunk_parent_chars
        self._child_chars = chunk_child_chars
        self._overlap_chars = chunk_overlap_chars
        self._classification_max_source_chars = classification_max_source_chars

    async def run(self, document_id: str) -> None:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            logger.warning("Ingestion requested for unknown document %s", document_id)
            return

        await self._documents.mark_processing(document_id)

        content = await self._storage.read(document.storage_path)
        extractor = get_extractor(document.original_filename)
        segments = await extractor(content, document.original_filename, self._llm)

        drafts = chunk_segments(
            segments,
            parent_chars=self._parent_chars,
            child_chars=self._child_chars,
            overlap_chars=self._overlap_chars,
        )
        chunks = await self._chunks.bulk_create(
            document_id=document_id, subject_id=document.subject_id, drafts=drafts
        )

        # Both classification and concept tagging work off parent chunks:
        # coherent, standalone units, rather than the smaller overlapping
        # child chunks used for retrieval.
        parent_chunks = [chunk for chunk in chunks if chunk.chunk_type == "parent"]
        if not parent_chunks:
            # No segments produced any usable text — e.g. a scanned PDF whose
            # pages all fell back to (and failed) vision transcription, or a
            # genuinely empty file. Left unchecked this would still reach
            # mark_ready() below, leaving the document stuck "ready" with no
            # chunks: quiz/exam/summary/chat generation would then fail with
            # a confusing "isn't ready yet (status: ready)" error. Raising
            # here instead routes through ingestion_task.py's except block,
            # which marks the document "failed" with an honest status.
            raise ExtractionError(
                document.original_filename, "no extractable text found (scanned, empty, or unreadable file)"
            )

        child_chunks = [chunk for chunk in chunks if chunk.chunk_type == "child"]
        if child_chunks:
            vectors = await self._embedder.embed_documents([chunk.content for chunk in child_chunks])
            await self._embeddings.bulk_create(
                chunk_ids=[chunk.id for chunk in child_chunks],
                vectors=vectors,
                model_name=self._embedder.model_name,
            )

        subject = await self._subjects.get_by_id(document.subject_id)
        source_text = self._join_capped(parent_chunks, self._classification_max_source_chars)
        await self._document_classifier.classify(
            document_id=document_id,
            curriculum_subject_id=subject.curriculum_subject_id if subject else None,
            source_text=source_text,
        )

        for chunk in parent_chunks:
            await self._concept_tagger.tag_chunk(
                subject_id=document.subject_id, chunk_id=chunk.id, chunk_content=chunk.content
            )

        page_numbers = [segment.page for segment in segments if segment.page is not None]
        page_count = max(page_numbers) if page_numbers else len(segments)
        await self._documents.mark_ready(document_id, page_count=page_count)

    @staticmethod
    def _join_capped(chunks: list, max_chars: int) -> str:
        pieces: list[str] = []
        total = 0
        for chunk in chunks:
            piece = chunk.content.strip()
            if total + len(piece) > max_chars:
                break
            pieces.append(piece)
            total += len(piece)
        return "\n\n".join(pieces)
