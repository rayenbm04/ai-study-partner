"""Turns a set of query strings (original question, HyDE hypothetical answer,
multi-query variations) into a ranked list of chunks to feed the answer LLM.

Each query variant is embedded and searched independently — different
phrasings surface different nearest neighbours — then the per-query result
lists are merged with Reciprocal Rank Fusion (RRF), which rewards chunks that
rank well across *multiple* variants without needing the raw distance scores
(which aren't comparable in a principled way across different query
embeddings) to be normalized or weighted by hand.

Retrieval happens over child chunks (small, embedding-friendly), but the text
handed to the answer LLM is the *parent* chunk's content where available —
enough surrounding context to answer from without diluting the embedding
target. Citations still reference the child chunk's page/section, since
that's the more precise location.
"""
from dataclasses import dataclass

from app.domain.entities.chunk import Chunk
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.embedding_repository import EmbeddingRepository
from app.services.embeddings.base import EmbeddingProvider

_RRF_K = 60  # standard RRF damping constant — de-emphasizes rank differences beyond the top few


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk: Chunk
    context_text: str  # parent content if available, else the chunk's own content
    fused_score: float


class VectorRetriever:
    def __init__(
        self,
        *,
        chunk_repo: ChunkRepository,
        embedding_repo: EmbeddingRepository,
        embedding_provider: EmbeddingProvider,
        top_k_per_query: int,
    ):
        self._chunks = chunk_repo
        self._embeddings = embedding_repo
        self._embedder = embedding_provider
        self._top_k_per_query = top_k_per_query

    async def retrieve(
        self, *, subject_id: str, queries: list[str], final_k: int, document_id: str | None = None
    ) -> list[RetrievedChunk]:
        """`queries` should already be deduplicated by the caller if desired;
        an empty or all-blank list returns no results rather than erroring.
        `document_id`, when given, narrows retrieval to that one document
        instead of the whole subject."""
        queries = [q for q in queries if q and q.strip()]
        if not queries:
            return []

        ranked_lists: list[list[str]] = []
        for query in queries:
            vector = await self._embedder.embed_query(query)
            results = await self._embeddings.search(
                subject_id=subject_id,
                query_vector=vector,
                top_k=self._top_k_per_query,
                model_name=self._embedder.model_name,
                document_id=document_id,
            )
            ranked_lists.append([chunk_id for chunk_id, _distance in results])

        fused_scores = _reciprocal_rank_fusion(ranked_lists)
        if not fused_scores:
            return []

        ordered_ids = [chunk_id for chunk_id, _score in sorted(
            fused_scores.items(), key=lambda item: item[1], reverse=True
        )][:final_k]

        chunks = await self._chunks.get_by_ids(ordered_ids)
        chunks_by_id = {chunk.id: chunk for chunk in chunks}

        parent_ids = {
            chunk.parent_chunk_id
            for chunk in chunks
            if chunk.parent_chunk_id is not None
        }
        parents_by_id = {}
        if parent_ids:
            parents = await self._chunks.get_by_ids(list(parent_ids))
            parents_by_id = {parent.id: parent for parent in parents}

        retrieved: list[RetrievedChunk] = []
        for chunk_id in ordered_ids:
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                continue  # chunk was deleted between search and fetch — skip rather than error
            parent = parents_by_id.get(chunk.parent_chunk_id) if chunk.parent_chunk_id else None
            context_text = parent.content if parent is not None else chunk.content
            retrieved.append(
                RetrievedChunk(chunk=chunk, context_text=context_text, fused_score=fused_scores[chunk_id])
            )
        return retrieved


def _reciprocal_rank_fusion(ranked_lists: list[list[str]]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, chunk_id in enumerate(ranked_list):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return scores
