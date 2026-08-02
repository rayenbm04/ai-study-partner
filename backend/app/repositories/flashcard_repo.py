from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.flashcard import Flashcard, FlashcardDraft
from app.domain.repositories.flashcard_repository import FlashcardRepository
from app.infrastructure.db.models.flashcard import FlashcardModel
from app.infrastructure.db.models.subject import SubjectModel


def _to_entity(model: FlashcardModel) -> Flashcard:
    return Flashcard(
        id=model.id,
        subject_id=model.subject_id,
        concept_id=model.concept_id,
        question=model.question,
        answer=model.answer,
        difficulty=model.difficulty,
        tags=list(model.tags or []),
        source=model.source,
        created_at=model.created_at,
    )


class SqlAlchemyFlashcardRepository(FlashcardRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def bulk_create(self, *, subject_id: str, drafts: list[FlashcardDraft]) -> list[Flashcard]:
        models = [
            FlashcardModel(
                subject_id=subject_id,
                concept_id=draft.concept_id,
                question=draft.question,
                answer=draft.answer,
                difficulty=draft.difficulty,
                tags=list(draft.tags),
                source=draft.source,
            )
            for draft in drafts
        ]
        self._session.add_all(models)
        await self._session.flush()
        for model in models:
            await self._session.refresh(model)
        return [_to_entity(m) for m in models]

    async def get_by_id(self, flashcard_id: str) -> Flashcard | None:
        model = await self._session.get(FlashcardModel, flashcard_id)
        return _to_entity(model) if model else None

    async def list_by_subject(self, subject_id: str) -> list[Flashcard]:
        stmt = select(FlashcardModel).where(FlashcardModel.subject_id == subject_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]

    async def list_by_user(self, user_id: str) -> list[Flashcard]:
        stmt = (
            select(FlashcardModel)
            .join(SubjectModel, SubjectModel.id == FlashcardModel.subject_id)
            .where(SubjectModel.user_id == user_id)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
