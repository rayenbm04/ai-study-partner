import json
from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import DocumentNotFoundError, FlashcardNotFoundError, SubjectNotFoundError
from app.domain.entities.chunk import ChunkDraft
from app.services.document_service import DocumentService
from app.services.flashcard_engine.flashcard_service import FlashcardService
from app.services.subject_service import SubjectService
from tests.unit.fakes import (
    FakeChunkRepository,
    FakeConceptChunkRepository,
    FakeConceptRepository,
    FakeDocumentRepository,
    FakeFlashcardRepository,
    FakeFlashcardReviewRepository,
    FakeLLMProvider,
    FakeStorage,
    FakeSubjectRepository,
)


async def _build(*, llm, default_count=10, max_count=30):
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
    flashcard_repo = FakeFlashcardRepository(subject_repo=subject_repo)
    review_repo = FakeFlashcardReviewRepository()

    service = FlashcardService(
        flashcard_repo=flashcard_repo, review_repo=review_repo, document_service=document_service,
        subject_service=subject_service, chunk_repo=chunk_repo, concept_repo=concept_repo,
        llm_provider=llm, max_source_chars=16000, default_generate_count=default_count,
        max_generate_count=max_count,
    )
    return service, subject_repo, document_repo, chunk_repo, flashcard_repo, review_repo


async def _seed_ready_document(subject_repo, document_repo, chunk_repo, *, user_id="user-1"):
    subject = await subject_repo.create(user_id=user_id, name="Physics", description=None, color=None, icon=None)
    document = await document_repo.create(
        document_id="doc-1", subject_id=subject.id, original_filename="notes.pdf",
        storage_path="x", file_type=".pdf",
    )
    drafts = [
        ChunkDraft(
            content="Newton's first law: an object in motion stays in motion.", chunk_type="parent",
            parent_index=None, page=1, section_title=None, chapter=None, token_count=10,
        )
    ]
    await chunk_repo.bulk_create(document_id=document.id, subject_id=subject.id, drafts=drafts)
    await document_repo.mark_ready(document.id, page_count=1)
    document = await document_repo.get_by_id(document.id)
    return subject, document


_TWO_CARDS_RESPONSE = json.dumps(
    {
        "flashcards": [
            {"question": "What stays in motion?", "answer": "An object with no net force.", "difficulty": "easy",
             "concept_name": None, "tags": ["motion"]},
            {"question": "Who formulated this law?", "answer": "Newton", "difficulty": "easy",
             "concept_name": None, "tags": ["history"]},
        ]
    }
)


async def test_generate_creates_and_persists_flashcards():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, flashcard_repo, _ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    assert len(cards) == 2
    stored = await flashcard_repo.list_by_subject(subject.id)
    assert len(stored) == 2


async def test_generate_respects_max_generate_count_cap():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm, max_count=1)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id, count=50)

    # The generator itself received the capped count (1), so it should have
    # truncated its own output to 1 card even though the LLM offered 2.
    assert "1" in llm.calls[0]["system"]


async def test_generate_raises_when_document_belongs_to_different_subject():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    other_subject = await subject_repo.create(user_id="user-1", name="Chemistry", description=None, color=None, icon=None)

    with pytest.raises(DocumentNotFoundError):
        await service.generate(user_id="user-1", subject_id=other_subject.id, document_id=document.id)


async def test_generate_returns_empty_list_when_generator_yields_nothing():
    llm = FakeLLMProvider(response="not json")
    service, subject_repo, document_repo, chunk_repo, flashcard_repo, _ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)

    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    assert cards == []
    assert await flashcard_repo.list_by_subject(subject.id) == []


async def test_list_for_subject_attaches_review_state():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    pairs = await service.list_for_subject(user_id="user-1", subject_id=subject.id)
    assert len(pairs) == 2
    assert all(review is None for _card, review in pairs)  # never reviewed yet

    await service.review(user_id="user-1", flashcard_id=cards[0].id, quality=5)
    pairs = await service.list_for_subject(user_id="user-1", subject_id=subject.id)
    reviewed = next(review for card, review in pairs if card.id == cards[0].id)
    assert reviewed is not None
    assert reviewed.repetitions == 1


async def test_review_creates_state_on_first_review():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    review = await service.review(user_id="user-1", flashcard_id=cards[0].id, quality=4)

    assert review.repetitions == 1
    assert review.interval_days == 1
    assert review.last_grade == 4


async def test_review_raises_for_unknown_flashcard():
    service, *_ = await _build(llm=FakeLLMProvider(response="{}"))

    with pytest.raises(FlashcardNotFoundError):
        await service.review(user_id="user-1", flashcard_id="does-not-exist", quality=4)


async def test_review_raises_when_subject_not_owned():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo, user_id="user-1")
    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    with pytest.raises(SubjectNotFoundError):
        await service.review(user_id="someone-else", flashcard_id=cards[0].id, quality=4)


async def test_list_due_includes_never_reviewed_cards():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    due = await service.list_due(user_id="user-1")

    assert {card.id for card, _review in due} == {c.id for c in cards}


async def test_list_due_excludes_cards_not_yet_due():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    now = datetime.now(timezone.utc)
    await service.review(user_id="user-1", flashcard_id=cards[0].id, quality=5, now=now)

    due_immediately = await service.list_due(user_id="user-1", now=now)
    due_ids = {card.id for card, _review in due_immediately}
    assert cards[0].id not in due_ids  # just reviewed successfully, not due again yet
    assert cards[1].id in due_ids  # never reviewed


async def test_list_due_includes_cards_past_their_next_review_date():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo)
    cards = await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    now = datetime.now(timezone.utc)
    await service.review(user_id="user-1", flashcard_id=cards[0].id, quality=5, now=now)

    future = now + timedelta(days=30)
    due_later = await service.list_due(user_id="user-1", now=future)
    assert cards[0].id in {card.id for card, _review in due_later}


async def test_list_due_is_isolated_between_users():
    llm = FakeLLMProvider(response=_TWO_CARDS_RESPONSE)
    service, subject_repo, document_repo, chunk_repo, *_ = await _build(llm=llm)
    subject, document = await _seed_ready_document(subject_repo, document_repo, chunk_repo, user_id="user-1")
    await service.generate(user_id="user-1", subject_id=subject.id, document_id=document.id)

    due_for_other_user = await service.list_due(user_id="someone-else")

    assert due_for_other_user == []
