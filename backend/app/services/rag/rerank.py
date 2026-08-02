"""Reranks retrieved chunks by actual relevance to the question.

RRF fusion (see retriever.py) is a decent proxy for relevance but only looks
at embedding-distance rank — it has no idea whether a chunk that happens to
be nearby in vector space actually *answers* the question. This module makes
one structured-JSON LLM call with the question and the candidate chunks and
asks it to score each one, so the final context sent to the answer LLM is
picked by something that actually read the text.

Deliberately not a local cross-encoder model: this pipeline stays cloud-only
end to end, and a single small LLM call is cheap enough on free-tier quotas
to run per chat turn.
"""
import json
import logging

from app.services.llm.base import LLMProvider
from app.services.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You rank study material excerpts by how useful each one is for answering a student's "
    "question. Respond with strict JSON only, matching this shape: "
    '{"scores": [{"index": <int>, "relevance": <0-1 float>}, ...]}. Include every excerpt index '
    "exactly once. A relevance of 0 means the excerpt is irrelevant to the question; 1 means it "
    "directly answers it."
)


async def rerank(
    *, llm_provider: LLMProvider, question: str, candidates: list[RetrievedChunk], keep_k: int
) -> list[RetrievedChunk]:
    """Falls back to the input order (already RRF-ranked), truncated to
    keep_k, if the LLM call fails or returns something unusable — reranking
    is a quality improvement, not a hard dependency for the chat to work."""
    if not candidates:
        return []
    if len(candidates) <= keep_k:
        return candidates

    excerpts = "\n\n".join(
        f"[{i}] {c.context_text[:1500]}" for i, c in enumerate(candidates)
    )
    prompt = f"Question: {question}\n\nExcerpts:\n{excerpts}"

    try:
        response_text = await llm_provider.complete(
            system=_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.0,
            response_json=True,
        )
        parsed = json.loads(response_text)
        scores_raw = parsed["scores"] if isinstance(parsed, dict) else None
        if not isinstance(scores_raw, list):
            raise ValueError("scores missing or not a list")

        scored: list[tuple[int, float]] = []
        for item in scores_raw:
            index = int(item["index"])
            relevance = float(item["relevance"])
            if 0 <= index < len(candidates):
                scored.append((index, relevance))

        if not scored:
            raise ValueError("no valid scored indices returned")

        scored.sort(key=lambda pair: pair[1], reverse=True)
        seen: set[int] = set()
        ordered: list[RetrievedChunk] = []
        for index, _score in scored:
            if index not in seen:
                seen.add(index)
                ordered.append(candidates[index])
        # Anything the LLM omitted keeps its original relative order at the end.
        for i, candidate in enumerate(candidates):
            if i not in seen:
                ordered.append(candidate)
        return ordered[:keep_k]

    except Exception:
        logger.exception("rerank LLM call failed, falling back to RRF order")
        return candidates[:keep_k]
