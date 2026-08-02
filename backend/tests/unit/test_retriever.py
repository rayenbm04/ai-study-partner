from app.domain.entities.chunk import ChunkDraft
from app.services.rag.retriever import VectorRetriever, _reciprocal_rank_fusion
from tests.unit.fakes import FakeChunkRepository, FakeEmbeddingProvider, FakeEmbeddingRepository


def _parent_draft(content: str, page: int) -> ChunkDraft:
    return ChunkDraft(
        content=content, chunk_type="parent", parent_index=None, page=page, section_title=None, chapter=None,
        token_count=len(content.split()),
    )


def _child_draft(content: str, parent_index: int, page: int) -> ChunkDraft:
    return ChunkDraft(
        content=content, chunk_type="child", parent_index=parent_index, page=page, section_title=None, chapter=None,
        token_count=len(content.split()),
    )


async def _seed_chunks(chunk_repo, embedding_repo, embedding_provider, *, subject_id, document_id):
    drafts = [
        _parent_draft("Derivatives measure the rate of change of a function.", page=1),
        _child_draft("The derivative of x^2 is 2x.", parent_index=0, page=1),
        _parent_draft("Integrals compute the area under a curve.", page=2),
        _child_draft("The integral of 2x is x^2 + C.", parent_index=2, page=2),
    ]
    chunks = await chunk_repo.bulk_create(document_id=document_id, subject_id=subject_id, drafts=drafts)
    child_chunks = [c for c in chunks if c.chunk_type == "child"]
    vectors = await embedding_provider.embed_documents([c.content for c in child_chunks])
    await embedding_repo.bulk_create(
        chunk_ids=[c.id for c in child_chunks], vectors=vectors, model_name=embedding_provider.model_name
    )
    return chunks


async def test_retrieve_returns_parent_context_for_matched_child():
    chunk_repo = FakeChunkRepository()
    embedding_repo = FakeEmbeddingRepository(chunk_repo=chunk_repo)
    embedder = FakeEmbeddingProvider(dimension=8)
    chunks = await _seed_chunks(chunk_repo, embedding_repo, embedder, subject_id="subj-1", document_id="doc-1")
    derivative_child = next(c for c in chunks if "derivative of x^2" in c.content)

    retriever = VectorRetriever(
        chunk_repo=chunk_repo, embedding_repo=embedding_repo, embedding_provider=embedder, top_k_per_query=5
    )
    results = await retriever.retrieve(
        subject_id="subj-1", queries=["The derivative of x^2 is 2x."], final_k=2
    )

    assert results
    top = results[0]
    assert top.chunk.id == derivative_child.id
    assert top.context_text == "Derivatives measure the rate of change of a function."


async def test_retrieve_filters_by_subject():
    chunk_repo = FakeChunkRepository()
    embedding_repo = FakeEmbeddingRepository(chunk_repo=chunk_repo)
    embedder = FakeEmbeddingProvider(dimension=8)
    await _seed_chunks(chunk_repo, embedding_repo, embedder, subject_id="subj-1", document_id="doc-1")

    retriever = VectorRetriever(
        chunk_repo=chunk_repo, embedding_repo=embedding_repo, embedding_provider=embedder, top_k_per_query=5
    )
    results = await retriever.retrieve(subject_id="subj-other", queries=["derivative"], final_k=5)

    assert results == []


async def test_retrieve_returns_empty_for_blank_queries():
    chunk_repo = FakeChunkRepository()
    embedding_repo = FakeEmbeddingRepository(chunk_repo=chunk_repo)
    embedder = FakeEmbeddingProvider(dimension=8)

    retriever = VectorRetriever(
        chunk_repo=chunk_repo, embedding_repo=embedding_repo, embedding_provider=embedder, top_k_per_query=5
    )
    results = await retriever.retrieve(subject_id="subj-1", queries=["", "   "], final_k=5)

    assert results == []


def test_reciprocal_rank_fusion_rewards_chunks_ranked_well_across_lists():
    fused = _reciprocal_rank_fusion([
        ["a", "b", "c"],
        ["b", "a", "d"],
    ])

    # "a" and "b" each appear near the top of both lists, so they should
    # outscore "c"/"d", which only appear once and further down.
    assert fused["a"] > fused["c"]
    assert fused["b"] > fused["d"]


def test_reciprocal_rank_fusion_handles_empty_lists():
    assert _reciprocal_rank_fusion([]) == {}
    assert _reciprocal_rank_fusion([[], []]) == {}
