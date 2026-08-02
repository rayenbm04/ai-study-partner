from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.entities.flashcard import Flashcard, FlashcardReview

Difficulty = Literal["easy", "medium", "hard"]


class FlashcardGenerateRequest(BaseModel):
    document_id: str
    count: int | None = Field(default=None, ge=1, le=100)


class FlashcardReviewRequest(BaseModel):
    quality: int = Field(ge=0, le=5, description="0-2 = lapse/forgot, 3-5 = recalled successfully, per SM-2")


class ReviewStateResponse(BaseModel):
    ease_factor: float
    interval_days: int
    repetitions: int
    last_grade: int | None
    last_reviewed_at: datetime | None
    next_review_date: datetime

    @classmethod
    def from_entity(cls, review: FlashcardReview) -> "ReviewStateResponse":
        return cls(
            ease_factor=review.ease_factor,
            interval_days=review.interval_days,
            repetitions=review.repetitions,
            last_grade=review.last_grade,
            last_reviewed_at=review.last_reviewed_at,
            next_review_date=review.next_review_date,
        )


class FlashcardResponse(BaseModel):
    id: str
    subject_id: str
    concept_id: str | None
    question: str
    answer: str
    difficulty: str
    tags: list[str]
    source: str
    created_at: datetime
    review: ReviewStateResponse | None = None

    @classmethod
    def from_entity(cls, flashcard: Flashcard, review: FlashcardReview | None = None) -> "FlashcardResponse":
        return cls(
            id=flashcard.id,
            subject_id=flashcard.subject_id,
            concept_id=flashcard.concept_id,
            question=flashcard.question,
            answer=flashcard.answer,
            difficulty=flashcard.difficulty,
            tags=flashcard.tags,
            source=flashcard.source,
            created_at=flashcard.created_at,
            review=ReviewStateResponse.from_entity(review) if review else None,
        )
