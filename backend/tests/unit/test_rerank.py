import json

from app.domain.entities.chunk import Chunk
from app.services.rag.rerank import rerank
from app.services.rag.retriever import RetrievedChunk
from tests.unit.fakes import FakeLLMProvider


def _candidate(id_: str, content: str, score: float) -> RetrievedChunk:
    chunk = Chunk(
        id=id_, document_id="doc-1", subject_id="subj-1", content=content, chunk_type="child",
        parent_chunk_id=None, page=1, section_title=None, chapter=None, token_count=len(content.split()),
    )
    return RetrievedChunk(chunk=chunk, context_text=content, fused_score=score)


async def test_rerank_reorders_by_llm_relevance_scores():
    # keep_k must be strictly less than len(candidates), or rerank() short-circuits
    # (returning the input order untouched) rather than bothering the LLM at all.
    candidates = [
        _candidate("a", "irrelevant text", 0.9),
        _candidate("b", "the actual answer", 0.5),
        _candidate("c", "also irrelevant", 0.4),
    ]
    llm = FakeLLMProvider(
        response=json.dumps(
            {"scores": [{"index": 0, "relevance": 0.1}, {"index": 1, "relevance": 0.95}, {"index": 2, "relevance": 0.05}]}
        )
    )

    result = await rerank(llm_provider=llm, question="q", candidates=candidates, keep_k=2)

    assert [c.chunk.id for c in result] == ["b", "a"]


async def test_rerank_truncates_to_keep_k():
    candidates = [_candidate(str(i), f"text {i}", 1.0) for i in range(5)]
    llm = FakeLLMProvider(
        response=json.dumps({"scores": [{"index": i, "relevance": 1.0 - i * 0.1} for i in range(5)]})
    )

    result = await rerank(llm_provider=llm, question="q", candidates=candidates, keep_k=2)

    assert len(result) == 2
    assert [c.chunk.id for c in result] == ["0", "1"]


async def test_rerank_skips_llm_call_when_already_at_or_under_keep_k():
    candidates = [_candidate("a", "text", 1.0)]
    llm = FakeLLMProvider(response="should not be used")

    result = await rerank(llm_provider=llm, question="q", candidates=candidates, keep_k=5)

    assert result == candidates
    assert llm.calls == []


async def test_rerank_falls_back_to_original_order_on_bad_json():
    candidates = [_candidate("a", "text a", 1.0), _candidate("b", "text b", 0.9), _candidate("c", "text c", 0.8)]
    llm = FakeLLMProvider(response="not json")

    result = await rerank(llm_provider=llm, question="q", candidates=candidates, keep_k=2)

    assert [c.chunk.id for c in result] == ["a", "b"]


async def test_rerank_falls_back_when_llm_raises():
    class BoomLLM(FakeLLMProvider):
        async def complete(self, **kwargs):
            raise RuntimeError("provider down")

    candidates = [_candidate("a", "text a", 1.0), _candidate("b", "text b", 0.9), _candidate("c", "text c", 0.8)]

    result = await rerank(llm_provider=BoomLLM(), question="q", candidates=candidates, keep_k=2)

    assert [c.chunk.id for c in result] == ["a", "b"]


async def test_rerank_appends_omitted_indices_at_the_end():
    candidates = [
        _candidate("a", "text a", 1.0), _candidate("b", "text b", 0.9),
        _candidate("c", "text c", 0.8), _candidate("d", "text d", 0.7),
    ]
    # LLM only scores index 2 ("c"); "a", "b", "d" were omitted from its response.
    llm = FakeLLMProvider(response=json.dumps({"scores": [{"index": 2, "relevance": 0.99}]}))

    result = await rerank(llm_provider=llm, question="q", candidates=candidates, keep_k=3)

    assert [c.chunk.id for c in result] == ["c", "a", "b"]


async def test_rerank_returns_empty_for_no_candidates():
    llm = FakeLLMProvider(response="{}")

    result = await rerank(llm_provider=llm, question="q", candidates=[], keep_k=5)

    assert result == []
