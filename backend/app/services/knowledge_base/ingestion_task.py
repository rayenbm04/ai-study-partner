"""Entry point for running ingestion outside the HTTP request that triggered
it. FastAPI's BackgroundTasks execute after the request's response has been
sent — and after the request's DB session has already been closed — so this
opens its own session rather than reusing anything request-scoped.

At production scale, this function is exactly what a task-queue worker
(Celery/RQ/arq) would call instead of FastAPI BackgroundTasks; nothing about
the pipeline itself would need to change, only what invokes it.
"""
import logging
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.storage.base import StoragePort
from app.infrastructure.storage.local_storage import LocalStorage
from app.repositories.chunk_repo import SqlAlchemyChunkRepository
from app.repositories.concept_chunk_repo import SqlAlchemyConceptChunkRepository
from app.repositories.concept_repo import SqlAlchemyConceptRepository
from app.repositories.curriculum_repo import SqlAlchemyCurriculumRepository
from app.repositories.document_repo import SqlAlchemyDocumentRepository
from app.repositories.embedding_repo import SqlAlchemyEmbeddingRepository
from app.repositories.subject_repo import SqlAlchemySubjectRepository
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.factory import build_embedding_provider
from app.services.knowledge_base.concept_tagger import ConceptTagger
from app.services.knowledge_base.document_classifier import DocumentClassifier
from app.services.knowledge_base.ingestion_pipeline import IngestionPipeline
from app.services.llm.base import LLMProvider
from app.services.llm.factory import build_llm_provider, build_simple_llm_provider

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AsyncSession]


def _build_pipeline(
    session: AsyncSession,
    *,
    storage: StoragePort,
    llm_provider: LLMProvider,
    simple_llm_provider: LLMProvider,
    embedding_provider: EmbeddingProvider,
) -> IngestionPipeline:
    document_repo = SqlAlchemyDocumentRepository(session)
    return IngestionPipeline(
        document_repo=document_repo,
        chunk_repo=SqlAlchemyChunkRepository(session),
        concept_chunk_repo=SqlAlchemyConceptChunkRepository(session),
        embedding_repo=SqlAlchemyEmbeddingRepository(session),
        subject_repo=SqlAlchemySubjectRepository(session),
        storage=storage,
        embedding_provider=embedding_provider,
        # Extraction (PDF vision fallback for scanned/image pages) stays on
        # the main model — image transcription quality matters and vision
        # calls are already infrequent by design (see extractors/pdf.py).
        llm_provider=llm_provider,
        # Concept tagging and document classification are both mechanical
        # classification/extraction tasks, not reasoning-heavy — and concept
        # tagging in particular is the highest-volume LLM call in ingestion
        # (one batch per handful of chunks), so this is where the cheaper
        # model matters most.
        concept_tagger=ConceptTagger(
            llm_provider=simple_llm_provider,
            concept_repo=SqlAlchemyConceptRepository(session),
            concept_chunk_repo=SqlAlchemyConceptChunkRepository(session),
            relevance_threshold=settings.concept_tag_relevance_threshold,
            max_new_concepts=settings.max_new_concepts_per_chunk,
        ),
        document_classifier=DocumentClassifier(
            llm_provider=simple_llm_provider,
            curriculum_repo=SqlAlchemyCurriculumRepository(session),
            document_repo=document_repo,
            confidence_threshold=settings.classification_confidence_threshold,
        ),
        chunk_parent_chars=settings.chunk_parent_chars,
        chunk_child_chars=settings.chunk_child_chars,
        chunk_overlap_chars=settings.chunk_overlap_chars,
        classification_max_source_chars=settings.classification_max_source_chars,
        concept_tag_batch_size=settings.concept_tag_batch_size,
    )


async def ingest_document_task(
    document_id: str,
    *,
    session_factory: SessionFactory = AsyncSessionLocal,
    storage: StoragePort | None = None,
    llm_provider: LLMProvider | None = None,
    simple_llm_provider: LLMProvider | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> None:
    resolved_storage = storage or LocalStorage(settings.storage_dir)
    resolved_llm = llm_provider or build_llm_provider(settings)
    resolved_simple_llm = simple_llm_provider or build_simple_llm_provider(settings)
    resolved_embedder = embedding_provider or build_embedding_provider(settings)

    async with session_factory() as session:
        pipeline = _build_pipeline(
            session, storage=resolved_storage, llm_provider=resolved_llm,
            simple_llm_provider=resolved_simple_llm, embedding_provider=resolved_embedder,
        )
        try:
            await pipeline.run(document_id)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Ingestion failed for document %s", document_id)
            await _mark_failed(document_id, session_factory)
            return

    # The document is committed as "ready" and already usable for RAG chat at
    # this point — concept tagging (the knowledge-graph enrichment powering
    # progress/planning) runs afterward, in its own transaction, so a failure
    # here never rolls back or un-readies a document whose RAG index is
    # already complete. Errors are logged, not re-raised: this step is a
    # best-effort background enhancement, not something a student is waiting
    # on to start chatting with their material.
    async with session_factory() as session:
        pipeline = _build_pipeline(
            session, storage=resolved_storage, llm_provider=resolved_llm,
            simple_llm_provider=resolved_simple_llm, embedding_provider=resolved_embedder,
        )
        try:
            await pipeline.tag_concepts(document_id)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Concept tagging failed for document %s — document remains ready, "
                "knowledge graph just wasn't enriched with it.",
                document_id,
            )


async def _mark_failed(document_id: str, session_factory: SessionFactory) -> None:
    async with session_factory() as session:
        repo = SqlAlchemyDocumentRepository(session)
        try:
            # The real exception goes to the logs above, not to students —
            # avoids leaking internals through the document status endpoint.
            await repo.mark_failed(document_id, error_message="Ingestion failed. Check server logs for details.")
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Could not record ingestion failure for document %s either", document_id)
