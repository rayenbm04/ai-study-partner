"""Orchestrates flashcard generation, listing, and SM-2 review — the
persistence/ownership layer around the pure sm2.py algorithm and the
LLM-based generator.py.

Review state (FlashcardReview) is created lazily on a card's first review
rather than seeded at generation time: a card with no review row is simply
"due now" (see list_due), so there's nothing to initialize until a student
actually studies it.
"""
import uuid
from datetime import datetime, timezone

from app.core.exceptions import DocumentNotFoundError, FlashcardNotFoundError
from app.domain.entities.flashcard import Flashcard, FlashcardReview
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.concept_repository import ConceptRepository
from app.domain.repositories.flashcard_repository import FlashcardRepository
from app.domain.repositories.flashcard_review_repository import FlashcardReviewRepository
from app.services.document_service import DocumentService
from app.services.flashcard_engine import sm2
from app.services.flashcard_engine.generator import generate_flashcards
from app.services.knowledge_base.document_source import build_document_source_text
from app.services.llm.base import LLMProvider
from app.services.subject_service import SubjectService


def _as_aware(value: datetime) -> datetime:
    """SQLite doesn't preserve tzinfo on DateTime(timezone=True) columns, so a
    value round-tripped through it on that backend comes back naive even
    though it was stored as UTC — normalize before comparing against an
    aware "now", matching the same fix already used in refresh_token_repo.py.
    Postgres doesn't need this (it round-trips tzinfo correctly), but the
    normalization is a no-op there since the value is already aware."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class FlashcardService:
    def __init__(
        self,
        *,
        flashcard_repo: FlashcardRepository,
        review_repo: FlashcardReviewRepository,
        document_service: DocumentService,
        subject_service: SubjectService,
        chunk_repo: ChunkRepository,
        concept_repo: ConceptRepository,
        llm_provider: LLMProvider,
        max_source_chars: int,
        default_generate_count: int,
        max_generate_count: int,
    ):
        self._flashcards = flashcard_repo
        self._reviews = review_repo
        self._documents = document_service
        self._subjects = subject_service
        self._chunks = chunk_repo
        self._concepts = concept_repo
        self._llm = llm_provider
        self._max_source_chars = max_source_chars
        self._default_generate_count = default_generate_count
        self._max_generate_count = max_generate_count

    async def generate(
        self,
        *,
        user_id: str,
        subject_id: str,
        document_id: str,
        count: int | None = None,
        language: str = "en",
    ) -> list[Flashcard]:
        document = await self._documents.get_owned(user_id, document_id)
        if document.subject_id != subject_id:
            raise DocumentNotFoundError(document_id)

        resolved_count = min(count or self._default_generate_count, self._max_generate_count)
        source_text = await build_document_source_text(self._chunks, document, self._max_source_chars)
        concepts = await self._concepts.list_by_document(document_id)

        drafts = await generate_flashcards(
            llm_provider=self._llm,
            document_filename=document.original_filename,
            source_text=source_text,
            concepts=concepts,
            count=resolved_count,
            language=language,
        )
        if not drafts:
            return []
        return await self._flashcards.bulk_create(subject_id=subject_id, drafts=drafts)

    async def list_for_subject(
        self, *, user_id: str, subject_id: str
    ) -> list[tuple[Flashcard, FlashcardReview | None]]:
        await self._subjects.get_owned(user_id, subject_id)
        flashcards = await self._flashcards.list_by_subject(subject_id)
        reviews_by_flashcard = {r.flashcard_id: r for r in await self._reviews.list_by_user(user_id)}
        return [(card, reviews_by_flashcard.get(card.id)) for card in flashcards]

    async def review(self, *, user_id: str, flashcard_id: str, quality: int, now: datetime | None = None) -> FlashcardReview:
        flashcard = await self._get_owned_flashcard(user_id, flashcard_id)
        reviewed_at = now or datetime.now(timezone.utc)

        existing = await self._reviews.get_by_flashcard_and_user(flashcard.id, user_id)
        if existing is None:
            base = sm2.initial_state(now=reviewed_at)
            ease_factor, interval_days, repetitions = base.ease_factor, base.interval_days, base.repetitions
        else:
            ease_factor, interval_days, repetitions = (
                existing.ease_factor, existing.interval_days, existing.repetitions
            )

        new_state = sm2.review(
            ease_factor=ease_factor, interval_days=interval_days, repetitions=repetitions,
            quality=quality, reviewed_at=reviewed_at,
        )

        return await self._reviews.upsert(
            flashcard_id=flashcard.id,
            user_id=user_id,
            ease_factor=new_state.ease_factor,
            interval_days=new_state.interval_days,
            repetitions=new_state.repetitions,
            last_grade=quality,
            last_reviewed_at=reviewed_at,
            next_review_date=new_state.next_review_date,
        )

    async def list_due(
        self, *, user_id: str, now: datetime | None = None
    ) -> list[tuple[Flashcard, FlashcardReview | None]]:
        as_of = now or datetime.now(timezone.utc)
        flashcards = await self._flashcards.list_by_user(user_id)
        reviews_by_flashcard = {r.flashcard_id: r for r in await self._reviews.list_by_user(user_id)}

        due: list[tuple[Flashcard, FlashcardReview | None]] = []
        for card in flashcards:
            review_state = reviews_by_flashcard.get(card.id)
            if review_state is None or _as_aware(review_state.next_review_date) <= as_of:
                due.append((card, review_state))
        return due

    async def get_review_state(self, *, user_id: str, flashcard_id: str) -> FlashcardReview | None:
        return await self._reviews.get_by_flashcard_and_user(flashcard_id, user_id)

    async def _get_owned_flashcard(self, user_id: str, flashcard_id: str) -> Flashcard:
        flashcard = await self._flashcards.get_by_id(flashcard_id)
        if flashcard is None:
            raise FlashcardNotFoundError(flashcard_id)
        await self._subjects.get_owned(user_id, flashcard.subject_id)  # 404s if this user doesn't own the subject
        return flashcard
