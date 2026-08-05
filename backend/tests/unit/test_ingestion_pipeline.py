import json

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
    # The shared fake LLM response has no "document_type" key, so classification
    # falls back to "other" defensively rather than raising.
    assert updated.document_type == "other"

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

    # one LLM call per parent chunk, plus one classification call for the document
    parent_count = len([c for c in chunks if c.chunk_type == "parent"])
    assert len(llm.calls) == parent_count + 1


async def test_run_classifies_document_type_and_links_curriculum_chapter():
    llm = FakeLLMProvider(
        responses=[
            json.dumps({"document_type": "cours", "chapter": "Circuits", "lesson": None, "confidence": 0.9}),
            *[json.dumps({"matched": [], "new_concepts": []})] * 10,
        ]
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


async def test_run_marks_processing_before_completing():
    pipeline, document_repo, _chunk_repo, _embedding_repo, _concept_repo, storage, _llm, *_ = _build_pipeline()
    document = await document_repo.create(
        document_id="doc-2", subject_id="subj-1", original_filename="short.txt", storage_path="subj-1/doc-2/short.txt", file_type=".txt"
    )
    await storage.save(subject_id="subj-1", document_id="doc-2", filename="short.txt", content=b"Tiny note.")

    assert (await document_repo.get_by_id("doc-2")).status == "pending"
    await pipeline.run(document.id)
    assert (await document_repo.get_by_id("doc-2")).status == "ready"
