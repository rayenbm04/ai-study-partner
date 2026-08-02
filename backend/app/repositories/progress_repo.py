from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.progress import Progress
from app.domain.repositories.progress_repository import ProgressRepository
from app.infrastructure.db.models.progress import ProgressModel


def _to_entity(model: ProgressModel) -> Progress:
    return Progress(
        id=model.id,
        user_id=model.user_id,
        concept_id=model.concept_id,
        mastery_score=model.mastery_score,
        trend=model.trend,
        last_updated=model.last_updated,
    )


class SqlAlchemyProgressRepository(ProgressRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, *, user_id, concept_id, mastery_score, trend) -> Progress:
        stmt = select(ProgressModel).where(
            ProgressModel.user_id == user_id, ProgressModel.concept_id == concept_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is not None:
            model.mastery_score = mastery_score
            model.trend = trend
        else:
            model = ProgressModel(user_id=user_id, concept_id=concept_id, mastery_score=mastery_score, trend=trend)
            self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_user_and_concept(self, user_id: str, concept_id: str) -> Progress | None:
        stmt = select(ProgressModel).where(
            ProgressModel.user_id == user_id, ProgressModel.concept_id == concept_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_user(self, user_id: str) -> list[Progress]:
        stmt = select(ProgressModel).where(ProgressModel.user_id == user_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
