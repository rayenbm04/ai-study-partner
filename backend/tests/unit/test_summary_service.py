import pytest

from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    InvalidSummaryTypeError,
    SubjectNotFoundError,
    SummaryNotFoundError,
)
from app.domain.entities.chunk import ChunkDraft
from app.services.document_service import DocumentService
from app.services.subject_service import SubjectService
from app.services.summary_engine.summary_service import SummaryService
from tests.unit.fakes import (
    FakeChunkRepository,
    FakeConceptChunkRepository,
    FakeConceptRepository,
    FakeDocumentRepository,
    FakeLLMProvider,
    FakeStorage,
    FakeSubjectRepository,
    FakeSummaryRepository,
)


async def _build(*, llm, max_source_chars=16000):
    subject_repo = FakeSubjectRepository()
    subject_service = SubjectService(subject_repo)
    document_repo = FakeDocumentRepository()
    document_service = DocumentService(
        document_repo=document_repo, subject_service=subject_service, storage=FakeStorage(),
        max_upload_bytes=50 * 1024 * 1024,
    )
    chunk_repo = FakeChunkRepository()
    concept_chunk_repo = FakeConceptChunkRepository()
    concept_repo = FakeConceptRepository(concept_chunk_repo=concept_chunk_repo, chunk_repo=chunk_repo)
    summary_repo = FakeSummaryRepository()

    service = SummaryService(
        summary_repo=summary_repo, document_service=document_service, chunk_repo=chunk_repo,
        concept_repo=concept_repo, llm_provider=llm, max_source_chars=max_source_chars,
    )
    return service, subject_repo, document_repo, chunk_repo, concept_repo, concept_chunk_repo, summary_repo


async def _seed_ready_document(subject_repo, document_repo, chunk_repo, *, user_id="user-1", pages=None):
    subject = await subject_repo.create(user_id=user_id, name="Physics", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="notes.pdf",
        storage_path="x", file_type=".pdf",
    )
    pages = pages or [(1, "Newton's first law: an object in motion stays in motion.")]
    drafts = [
        ChunkDraft(
            content=content, chunk_type="parent", parent_index=None, page=page, section_title=None,
            chapter=None, token_count=len(content.split()),
        )
        for page, content in pages
    ]
    await chunk_repo.bulk_create(document_id=document.id, subject_id=subject.id, drafts=drafts)
    await document_repo.mark_ready(document.id, page_count=len(pages))
    document = await document_repo.get_by_id(document.id)
    return subject, document


async def test_generate_calls_llm_and_caches_result():
    llm = FakeLLMProvider(response="A concise summary of Newton's first law.")
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    summary = await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
    )

    assert summary.content == "A concise summary of Newton's first law."
    assert summary.summary_type == "short"
    assert summary.document_id == document.id
    assert len(llm.calls) == 1
    assert "Newton's first law" in llm.calls[0]["prompt"]


async def test_generate_then_get_cached_returns_same_summary():
    llm = FakeLLMProvider(response="cached content")
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    generated = await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="bullet"
    )
    fetched = await service.get_cached(user_id="user-1", document_id=document.id, summary_type="bullet")

    assert fetched.id == generated.id
    assert fetched.content == "cached content"


async def test_regenerate_overwrites_previous_content():
    llm = FakeLLMProvider(responses=["first version", "second version"])
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    first = await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
    )
    second = await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
    )

    assert first.id == second.id  # same cache row, upserted in place
    assert second.content == "second version"
    fetched = await service.get_cached(user_id="user-1", document_id=document.id, summary_type="short")
    assert fetched.content == "second version"


async def test_get_cached_raises_when_never_generated():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    with pytest.raises(SummaryNotFoundError):
        await service.get_cached(user_id="user-1", document_id=document.id, summary_type="detailed")


async def test_generate_rejects_invalid_summary_type():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    with pytest.raises(InvalidSummaryTypeError):
        await service.generate(
            user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="haiku"
        )


async def test_get_cached_rejects_invalid_summary_type():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    with pytest.raises(InvalidSummaryTypeError):
        await service.get_cached(user_id="user-1", document_id=document.id, summary_type="haiku")


async def test_generate_raises_when_subject_not_owned():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo, user_id="user-1")

    # DocumentService.get_owned checks subject ownership internally and raises
    # SubjectNotFoundError (not DocumentNotFoundError) when the document exists
    # but belongs to a subject this user doesn't own.
    with pytest.raises(SubjectNotFoundError):
        await service.generate(
            user_id="someone-else", subject_id=subject.id, document_id=document.id, summary_type="short"
        )


async def test_generate_raises_when_document_belongs_to_different_subject():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    other_subject = await subject_repo.create(
        user_id="user-1", name="Chemistry", description=None, color=None, icon=None
    )

    with pytest.raises(DocumentNotFoundError):
        await service.generate(
            user_id="user-1", subject_id=other_subject.id, document_id=document.id, summary_type="short"
        )


async def test_generate_raises_when_document_not_ready():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject = await subject_repo.create(user_id="user-1", name="Physics", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="notes.pdf",
        storage_path="x", file_type=".pdf",
    )
    # never marked ready — still "pending"

    with pytest.raises(DocumentNotReadyError):
        await service.generate(
            user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
        )


async def test_generate_raises_when_ready_document_has_no_parent_chunks():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject = await subject_repo.create(user_id="user-1", name="Physics", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="notes.pdf",
        storage_path="x", file_type=".pdf",
    )
    await document_repo.mark_ready(document.id, page_count=1)  # ready, but no chunks were ever created

    with pytest.raises(DocumentNotReadyError):
        await service.generate(
            user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
        )


async def test_key_concepts_prompt_is_grounded_in_the_concept_graph():
    llm = FakeLLMProvider(response="**Inertia** — resists changes in motion.")
    service, subject_repo, document_repo, chunk_repo, concept_repo, concept_chunk_repo, _ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    concept = await concept_repo.create(subject_id=subject.id, name="Inertia", description="Resistance to change in motion")
    chunks = await chunk_repo.list_by_document(document.id)
    await concept_chunk_repo.link(concept_id=concept.id, chunk_id=chunks[0].id, relevance=0.9)

    await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="key_concepts"
    )

    assert "Inertia" in llm.calls[0]["prompt"]
    assert "concept graph" in llm.calls[0]["prompt"]


async def test_non_key_concepts_types_do_not_query_the_concept_graph():
    llm = FakeLLMProvider(response="plain summary")
    service, subject_repo, document_repo, chunk_repo, concept_repo, concept_chunk_repo, _ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
    )

    assert "concept graph" not in llm.calls[0]["prompt"]


async def test_source_text_assembled_in_page_order():
    llm = FakeLLMProvider(response="ok")
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(
        subject_repo, document_repo, chunk_repo,
        pages=[(3, "third page content"), (1, "first page content"), (2, "second page content")],
    )

    await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
    )

    prompt = llm.calls[0]["prompt"]
    assert prompt.index("first page content") < prompt.index("second page content") < prompt.index("third page content")


async def test_list_for_document_returns_all_generated_types():
    llm = FakeLLMProvider(responses=["short version", "bullet version"])
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short")
    await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="bullet")

    summaries = await service.list_for_document(user_id="user-1", document_id=document.id)

    assert {s.summary_type for s in summaries} == {"short", "bullet"}


async def test_list_for_document_raises_when_not_owned():
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=FakeLLMProvider(response="x"))
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo, user_id="user-1")

    with pytest.raises(SubjectNotFoundError):
        await service.list_for_document(user_id="someone-else", document_id=document.id)


async def test_source_text_truncated_beyond_max_source_chars():
    llm = FakeLLMProvider(response="ok")
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm, max_source_chars=10)
    subject, document = await _seed_ready_document(
        subject_repo, document_repo, chunk_repo,
        pages=[(1, "this is way more than ten characters of content")],
    )

    await service.generate(
        user_id="user-1", subject_id=subject.id, document_id=document.id, summary_type="short"
    )

    prompt = llm.calls[0]["prompt"]
    assert "truncated" in prompt
    assert "this is way more than ten characters of content" not in prompt
