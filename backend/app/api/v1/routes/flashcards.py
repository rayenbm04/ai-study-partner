from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_flashcard_service
from app.api.v1.schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardResponse,
    FlashcardReviewRequest,
    ReviewStateResponse,
)
from app.domain.entities.user import User
from app.services.flashcard_engine.flashcard_service import FlashcardService

router = APIRouter(tags=["flashcards"])


@router.post("/subjects/{subject_id}/flashcards/generate", response_model=list[FlashcardResponse])
async def generate_flashcards(
    subject_id: str,
    body: FlashcardGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: FlashcardService = Depends(get_flashcard_service),
) -> list[FlashcardResponse]:
    flashcards = await service.generate(
        user_id=current_user.id, subject_id=subject_id, document_id=body.document_id, count=body.count
    )
    return [FlashcardResponse.from_entity(card) for card in flashcards]


@router.get("/subjects/{subject_id}/flashcards", response_model=list[FlashcardResponse])
async def list_flashcards(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: FlashcardService = Depends(get_flashcard_service),
) -> list[FlashcardResponse]:
    pairs = await service.list_for_subject(user_id=current_user.id, subject_id=subject_id)
    return [FlashcardResponse.from_entity(card, review) for card, review in pairs]


@router.get("/flashcards/due", response_model=list[FlashcardResponse])
async def list_due_flashcards(
    current_user: User = Depends(get_current_user),
    service: FlashcardService = Depends(get_flashcard_service),
) -> list[FlashcardResponse]:
    pairs = await service.list_due(user_id=current_user.id)
    return [FlashcardResponse.from_entity(card, review) for card, review in pairs]


@router.post("/flashcards/{flashcard_id}/review", response_model=ReviewStateResponse)
async def review_flashcard(
    flashcard_id: str,
    body: FlashcardReviewRequest,
    current_user: User = Depends(get_current_user),
    service: FlashcardService = Depends(get_flashcard_service),
) -> ReviewStateResponse:
    review = await service.review(user_id=current_user.id, flashcard_id=flashcard_id, quality=body.quality)
    return ReviewStateResponse.from_entity(review)
