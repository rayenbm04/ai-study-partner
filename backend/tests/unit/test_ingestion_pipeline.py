import json
import math

import pytest

from app.core.exceptions import ExtractionError
from app.services.knowledge_base.concept_tagger import ConceptTagger
from app.services.knowledge_base.document_classifier import DocumentClassifier
from app.services.knowledge_base.ingestion_pipeline import IngestionPipeline
from tests.unit.fakes import (
    FakeChunkRepository,
    FakeConceptChunkRepository,
    FakeConceptRepository,
    FakeCurriculumRepository,
    FakeDocumentRepository,
    FakeEmbeddingProvider,
    FakeEmbeddingRepository,
    FakeLLMProvider,
    FakeStorage,
    FakeSubjectRepository,
)


def _build_pipeline(*, llm_response: str = '{"matched": [], "new_concepts": []}', llm=None):
    document_repo = FakeDocumentRepository()
    chunk_repo = FakeChunkRepository()
    concept_repo = FakeConceptRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    embedding_repo = FakeEmbeddingRepository()
    subject_repo = FakeSubjectRepository()
    curriculum_repo = FakeCurriculumRepository()
    storage = FakeStorage()
    embedder = FakeEmbeddingProvider(dimension=4)
    llm = llm if llm is not None else FakeLLMProvider(response=llm_response)

    pipeline = IngestionPipeline(
        document_repo=document_repo,
        chunk_repo=chunk_repo,
        concept_chunk_repo=concept_chunk_repo,
        embedding_repo=embedding_repo,
        subject_repo=subject_repo,
        storage=storage,
        embedding_provider=embedder,
        llm_provider=llm,
        concept_tagger=ConceptTagger(
            llm_provider=llm,
            concept_repo=concept_repo,
            concept_chunk_repo=concept_chunk_repo,
            relevance_threshold=0.5,
            max_new_concepts=3,
        ),
        document_classifier=DocumentClassifier(
            llm_provider=llm, curriculum_repo=curriculum_repo, document_repo=document_repo, confidence_threshold=0.5
        ),
        chunk_parent_chars=200,
        chunk_child_chars=60,
        chunk_overlap_chars=10,
        classification_max_source_chars=2000,
    )
    return pipeline, document_repo, chunk_repo, embedding_repo, concept_repo, storage, llm, subject_repo, curriculum_repo


async def test_run_processes_document_end_to_end():
    pipeline, document_repo, chunk_repo, embedding_repo, concept_repo, storage, llm, *_ = _build_pipeline(
        llm_response=json.dumps({"document_type": "other"})
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
    assert updated.document_type == "other"

    chunks = await chunk_repo.list_by_document("doc-1")
    assert any(c.chunk_type == "parent" for c in chunks)
    assert any(c.chunk_type == "child" for c in chunks)

    child_ids = {c.id for c in chunks if c.chunk_type == "child"}
    assert child_ids == set(embedding_repo.stored.keys())
    for vector, model_name in embedding_repo.stored.values():
        assert len(vector) == 4
        assert model_name == "fake-embedder"

    # Concept tagging is NOT part of run() — it's a separate, best-effort
    # follow-up (see tag_concepts() tests below) so "ready" doesn't wait on
    # one LLM call per parent chunk.
    assert await concept_repo.list_by_subject("subj-1") == []
    assert len(llm.calls) == 1  # just the one classification call


async def test_tag_concepts_batches_parent_chunks_into_few_llm_calls():
    """The whole point of tag_concepts(): tagging N parent chunks should take
    ceil(N / batch_size) LLM calls, not N — this is the fix for ingestion
    firing one LLM call per chunk on large documents."""
    pipeline, document_repo, chunk_repo, _embedding_repo, concept_repo, storage, llm, *_ = _build_pipeline(
        llm_response=json.dumps(
            {"chunks": [{"index": 0, "matched": [], "new_concepts": [
                {"name": "Ohm's Law", "description": "V=IR", "prerequisites": []}
            ]}]}
        )
    )
    document = await document_repo.create(
        document_id="doc-1", subject_id="subj-1", original_filename="notes.txt", storage_path="subj-1/doc-1/notes.txt", file_type=".txt"
    )
    # Long enough to produce several parent chunks at the test's chunk_parent_chars=200.
    content = ("Ohm's law relates voltage, current, and resistance. " * 40).encode("utf-8")
    await storage.save(subject_id="subj-1", document_id="doc-1", filename="notes.txt", content=content)
    await pipeline.run(document.id)
    llm.calls.clear()  # drop the classification call from run() — only count tag_concepts' calls

    await pipeline.tag_concepts(document.id)

    chunks = await chunk_repo.list_by_document("doc-1")
    parent_count = len([c for c in chunks if c.chunk_type == "parent"])
    assert parent_count > 6  # otherwise this test isn't exercising batching at all
    assert len(llm.calls) == math.ceil(parent_count / 6)  # default concept_tag_batch_size

    concepts = await concept_repo.list_by_subject("subj-1")
    assert any(c.name == "Ohm's Law" for c in concepts)


async def test_tag_concepts_on_document_with_no_chunks_does_not_raise():
    pipeline, *_ = _build_pipeline()
    await pipeline.tag_concepts("does-not-exist")  # should just no-op


async def test_run_classifies_document_type_and_links_curriculum_chapter():
    llm = FakeLLMProvider(
        response=json.dumps({"document_type": "cours", "chapter": "Circuits", "lesson": None, "confidence": 0.9})
    )
    pipeline, document_repo, chunk_repo, _embedding_repo, _concept_repo, storage, _llm, subject_repo, curriculum_repo = (
        _build_pipeline(llm=llm)
    )
    subject = await subject_repo.create(user_id="user-1", name="Physics", description=None, color=None, icon=None)
    curriculum_subject = await curriculum_repo.create_subject(academic_level_id="lvl-1", section_id=None, name="Physics")
    chapter = await curriculum_repo.create_chapter(curriculum_subject_id=curriculum_subject.id, name="Circuits", order_index=0)
    await subject_repo.update(subject.id, curriculum_subject_id=curriculum_subject.id)

    document = await document_repo.create(
        document_id="doc-3", subject_id=subject.id, original_filename="lecture.txt",
        storage_path=f"{subject.id}/doc-3/lecture.txt", file_type=".txt",
    )
    content = ("Ohm's law relates voltage, current, and resistance. " * 10).encode("utf-8")
    await storage.save(subject_id=subject.id, document_id="doc-3", filename="lecture.txt", content=content)

    await pipeline.run(document.id)

    updated = await document_repo.get_by_id("doc-3")
    assert updated.document_type == "cours"
    assert updated.chapter_id == chapter.id


async def test_run_on_unknown_document_does_not_raise():
    pipeline, *_ = _build_pipeline()
    await pipeline.run("does-not-exist")  # should just log and return


async def test_run_raises_extraction_error_when_no_chunks_produced():
    """A document whose extraction yields no usable text (blank file, scanned
    PDF with a failed vision fallback, etc.) must not sail through to
    mark_ready() with zero chunks — that leaves it stuck "ready" but unusable
    by every downstream feature. The pipeline should raise instead, so the
    caller (ingestion_task.py) marks it "failed" with an honest status."""
    pipeline, document_repo, chunk_repo, _embedding_repo, _concept_repo, storage, _llm, *_ = _build_pipeline()
    document = await document_repo.create(
        document_id="doc-empty", subject_id="subj-1", original_filename="blank.txt",
        storage_path="subj-1/doc-empty/blank.txt", file_type=".txt",
    )
    await storage.save(subject_id="subj-1", document_id="doc-empty", filename="blank.txt", content=b"   \n\n  ")

    with pytest.raises(ExtractionError):
        await pipeline.run(document.id)

    # Pipeline itself doesn't touch status on failure (that's ingestion_task's
    # job) — it should still be sitting at "processing" from earlier in run().
    assert (await document_repo.get_by_id("doc-empty")).status == "processing"
    assert await chunk_repo.list_by_document("doc-empty") == []


async def test_run_marks_processing_before_completing():
    pipeline, document_repo, _chunk_repo, _embedding_repo, _concept_repo, storage, _llm, *_ = _build_pipeline()
    document = await document_repo.create(
        document_id="doc-2", subject_id="subj-1", original_filename="short.txt", storage_path="subj-1/doc-2/short.txt", file_type=".txt"
    )
    await storage.save(subject_id="subj-1", document_id="doc-2", filename="short.txt", content=b"Tiny note.")

    assert (await document_repo.get_by_id("doc-2")).status == "pending"
    await pipeline.run(document.id)
    assert (await document_repo.get_by_id("doc-2")).status == "ready"
