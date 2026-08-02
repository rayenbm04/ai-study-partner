from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.flashcard import FlashcardReview
from app.domain.repositories.flashcard_review_repository import FlashcardReviewRepository
from app.infrastructure.db.models.flashcard_review import FlashcardReviewModel


def _to_entity(model: FlashcardReviewModel) -> FlashcardReview:
    return FlashcardReview(
        id=model.id,
        flashcard_id=model.flashcard_id,
        user_id=model.user_id,
        ease_factor=model.ease_factor,
        interval_days=model.interval_days,
        repetitions=model.repetitions,
        last_grade=model.last_grade,
        last_reviewed_at=model.last_reviewed_at,
        next_review_date=model.next_review_date,
    )


class SqlAlchemyFlashcardReviewRepository(FlashcardReviewRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(
        self, *, flashcard_id, user_id, ease_factor, interval_days, repetitions, last_grade,
        last_reviewed_at, next_review_date,
    ) -> FlashcardReview:
        stmt = select(FlashcardReviewModel).where(
            FlashcardReviewModel.flashcard_id == flashcard_id, FlashcardReviewModel.user_id == user_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            model.ease_factor = ease_factor
            model.interval_days = interval_days
            model.repetitions = repetitions
            model.last_grade = last_grade
            model.last_reviewed_at = last_reviewed_at
            model.next_review_date = next_review_date
        else:
            model = FlashcardReviewModel(
                flashcard_id=flashcard_id, user_id=user_id, ease_factor=ease_factor,
                interval_days=interval_days, repetitions=repetitions, last_grade=last_grade,
                last_reviewed_at=last_reviewed_at, next_review_date=next_review_date,
            )
            self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_flashcard_and_user(self, flashcard_id: str, user_id: str) -> FlashcardReview | None:
        stmt = select(FlashcardReviewModel).where(
            FlashcardReviewModel.flashcard_id == flashcard_id, FlashcardReviewModel.user_id == user_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_user(self, user_id: str) -> list[FlashcardReview]:
        stmt = select(FlashcardReviewModel).where(FlashcardReviewModel.user_id == user_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
