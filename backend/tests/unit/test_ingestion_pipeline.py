import json

from app.services.knowledge_base.concept_tagger import ConceptTagger
from app.services.knowledge_base.ingestion_pipeline import IngestionPipeline
from tests.unit.fakes import (
    FakeChunkRepository,
    FakeConceptChunkRepository,
    FakeConceptRepository,
    FakeDocumentRepository,
    FakeEmbeddingProvider,
    FakeEmbeddingRepository,
    FakeLLMProvider,
    FakeStorage,
)


def _build_pipeline(*, llm_response: str = '{"matched": [], "new_concepts": []}'):
    document_repo = FakeDocumentRepository()
    chunk_repo = FakeChunkRepository()
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    embedding_repo = FakeEmbeddingRepository()
    storage = FakeStorage()
    embedder = FakeEmbeddingProvider(dimension=4)
    llm = FakeLLMProvider(response=llm_response)

    pipeline = IngestionPipeline(
        document_repo=document_repo,
        chunk_repo=chunk_repo,
        concept_chunk_repo=concept_chunk_repo,
        embedding_repo=embedding_repo,
        storage=storage,
        embedding_provider=embedder,
        concept_tagger=ConceptTagger(
            llm_provider=llm,
            concept_repo=concept_repo,
            concept_chunk_repo=concept_chunk_repo,
            relevance_threshold=0.5,
            max_new_concepts=3,
        ),
        chunk_parent_chars=200,
        chunk_child_chars=60,
        chunk_overlap_chars=10,
    )
    return pipeline, document_repo, chunk_repo, embedding_repo, concept_repo, storage, llm


async def test_run_processes_document_end_to_end():
    pipeline, document_repo, chunk_repo, embedding_repo, concept_repo, storage, llm = _build_pipeline(
        llm_response=json.dumps({"matched": [], "new_concepts": [{"name": "Ohm's Law", "description": "V=IR", "prerequisites": []}]})
    )

    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="notes.txt", storage_path="subj-1/doc-1/notes.txt", file_type=".txt"
    )
    content = ("Ohm's law relates voltage, current, and resistance. " * 10).encode("utf-8")
    await storage.save(subject_id="subj-1", document_id="doc-1", filename="notes.txt", content=content)
    # FakeStorage.save() already wrote it at the same path document.storage_path points to.

    await pipeline.run(document.id)

    updated = await document_repo.get_by_id("doc-1")
    assert updated.status == "ready"
    assert updated.page_count is not None
    assert updated.error_message is None

    chunks = await chunk_repo.list_by_document("doc-1")
    assert any(c.chunk_type == "parent" for c in chunks)
    assert any(c.chunk_type == "child" for c in chunks)

    child_ids = {c.id for c in chunks if c.chunk_type == "child"}
    assert child_ids == set(embedding_repo.stored.keys())
    for vector, model_name in embedding_repo.stored.values():
        assert len(vector) == 4
        assert model_name == "fake-embedder"

    concepts = await concept_repo.list_by_subject("subj-1")
    assert any(c.name == "Ohm's Law" for c in concepts)

    # one LLM call per parent chunk
    parent_count = len([c for c in chunks if c.chunk_type == "parent"])
    assert len(llm.calls) == parent_count


async def test_run_on_unknown_document_does_not_raise():
    pipeline, *_ = _build_pipeline()
    await pipeline.run("does-not-exist")  # should just log and return


async def test_run_marks_processing_before_completing():
    pipeline, document_repo, *_ , storage, _llm = _build_pipeline()
    document = await document_repo.create(
        document_id="doc-2", subject_id="subj-1", original_filename="short.txt", storage_path="subj-1/doc-2/short.txt", file_type=".txt"
    )
    await storage.save(subject_id="subj-1", document_id="doc-2", filename="short.txt", content=b"Tiny note.")

    assert (await document_repo.get_by_id("doc-2")).status == "pending"
    await pipeline.run(document.id)
    assert (await document_repo.get_by_id("doc-2")).status == "ready"
