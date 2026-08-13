"""Orchestrates one document from stored bytes to a searchable set of
chunks: extract -> chunk -> embed -> classify -> mark ready.

Concept tagging (populating the subject's knowledge graph) is *not* part of
run() — it's the ingestion step with the most LLM calls (one batch per
handful of chunks, vs. one call total for classification), and nothing about
RAG chat depends on it. Splitting it into the separate tag_concepts() method
lets the caller (ingestion_task.py) commit "ready" as soon as the document is
actually usable for chat, then run concept tagging as a best-effort follow-up
in its own transaction — a failure there never un-readies a document that's
already fully indexed.

Deliberately has no exception handling of its own — status transitions on
failure are the caller's job (see ingestion_task.py), so this class stays a
straightforward, fully unit-testable sequence of steps against fakes.
"""
import logging
import time

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
        concept_tag_batch_size: int = 6,
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
        self._concept_tag_batch_size = max(1, concept_tag_batch_size)

    async def run(self, document_id: str) -> None:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            logger.warning("Ingestion requested for unknown document %s", document_id)
            return

        started_at = time.monotonic()
        await self._documents.mark_processing(document_id)
        await self._documents.update_progress(document_id, step="extracting", progress=10)

        content = await self._storage.read(document.storage_path)
        extractor = get_extractor(document.original_filename)
        segments = await extractor(content, document.original_filename, self._llm)

        await self._documents.update_progress(document_id, step="chunking", progress=35)
        drafts = chunk_segments(
            segments,
            parent_chars=self._parent_chars,
            child_chars=self._child_chars,
            overlap_chars=self._overlap_chars,
        )
        chunks = await self._chunks.bulk_create(
            document_id=document_id, subject_id=document.subject_id, drafts=drafts
        )

        # Classification works off parent chunks: coherent, standalone units,
        # rather than the smaller overlapping child chunks used for retrieval.
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
            await self._documents.update_progress(document_id, step="embedding", progress=55)
            vectors = await self._embedder.embed_documents([chunk.content for chunk in child_chunks])
            await self._embeddings.bulk_create(
                chunk_ids=[chunk.id for chunk in child_chunks],
                vectors=vectors,
                model_name=self._embedder.model_name,
            )

        await self._documents.update_progress(document_id, step="classifying", progress=85)
        subject = await self._subjects.get_by_id(document.subject_id)
        source_text = self._join_capped(parent_chunks, self._classification_max_source_chars)
        await self._document_classifier.classify(
            document_id=document_id,
            curriculum_subject_id=subject.curriculum_subject_id if subject else None,
            source_text=source_text,
        )

        page_numbers = [segment.page for segment in segments if segment.page is not None]
        page_count = max(page_numbers) if page_numbers else len(segments)
        await self._documents.mark_ready(document_id, page_count=page_count)

        logger.info(
            "Document %s ready: pages=%d parent_chunks=%d child_chunks=%d elapsed=%.1fs",
            document_id, page_count, len(parent_chunks), len(child_chunks), time.monotonic() - started_at,
        )

    async def tag_concepts(self, document_id: str) -> None:
        """Best-effort follow-up to run(): tags every parent chunk of an
        already-ready document against the subject's concept graph, batched
        concept_tag_batch_size chunks per LLM call. Safe to call multiple
        times (concept matching/creation is idempotent-ish — re-tagging just
        re-links/re-proposes, see ConceptTagger). Callers should treat any
        exception here as non-fatal to the document's ready status."""
        chunks = await self._chunks.list_by_document(document_id)
        parent_chunks = [chunk for chunk in chunks if chunk.chunk_type == "parent"]
        if not parent_chunks:
            return

        subject_id = parent_chunks[0].subject_id
        started_at = time.monotonic()
        batch_count = 0
        for start in range(0, len(parent_chunks), self._concept_tag_batch_size):
            batch = parent_chunks[start : start + self._concept_tag_batch_size]
            await self._concept_tagger.tag_chunks(
                subject_id=subject_id, chunks=[(chunk.id, chunk.content) for chunk in batch]
            )
            batch_count += 1

        logger.info(
            "Concept tagging done for document %s: parent_chunks=%d llm_calls=%d elapsed=%.1fs",
            document_id, len(parent_chunks), batch_count, time.monotonic() - started_at,
        )

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
