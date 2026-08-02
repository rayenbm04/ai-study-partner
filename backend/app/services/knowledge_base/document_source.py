"""Assembles a single document's ingested content into one text blob for a
downstream LLM call — shared by any feature scoped to exactly one document
(Phase 5's summary engine, Phase 6's flashcard generator) rather than needing
vector retrieval across a whole subject the way RAG chat does.

Uses parent chunks (already-sized context windows from ingestion, not the
small child chunks meant for embedding) concatenated in page order, capped at
a caller-supplied character budget so a huge document doesn't blow a
free-tier context window or turn a cheap feature into an expensive call.
"""
from app.core.exceptions import DocumentNotReadyError
from app.domain.entities.document import Document
from app.domain.repositories.chunk_repository import ChunkRepository


async def build_document_source_text(chunk_repo: ChunkRepository, document: Document, max_chars: int) -> str:
    chunks = await chunk_repo.list_by_document(document.id)
    parents = sorted(
        (c for c in chunks if c.chunk_type == "parent"), key=lambda c: c.page if c.page is not None else 0
    )
    if not parents:
        # A document marked "ready" should always have parent chunks — if it
        # doesn't, ingestion produced nothing usable, and that's a readiness
        # problem, not a prompting one.
        raise DocumentNotReadyError(document.id, document.status)

    pieces: list[str] = []
    total = 0
    truncated = False
    for chunk in parents:
        piece = chunk.content.strip()
        if total + len(piece) > max_chars:
            truncated = True
            break
        pieces.append(piece)
        total += len(piece)

    text = "\n\n".join(pieces)
    if truncated:
        text += "\n\n[Note: source material was truncated for length; this may not cover the entire document.]"
    return text
