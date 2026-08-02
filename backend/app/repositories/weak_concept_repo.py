from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.progress import WeakConcept
from app.domain.repositories.weak_concept_repository import WeakConceptRepository
from app.infrastructure.db.models.weak_concept import WeakConceptModel


def _to_entity(model: WeakConceptModel) -> WeakConcept:
    return WeakConcept(
        id=model.id,
        user_id=model.user_id,
        concept_id=model.concept_id,
        reason=model.reason,
        confidence=model.confidence,
        status=model.status,
        detected_at=model.detected_at,
    )


class SqlAlchemyWeakConceptRepository(WeakConceptRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, *, user_id: str, concept_id: str, reason: str, confidence: float) -> WeakConcept:
        model = WeakConceptModel(user_id=user_id, concept_id=concept_id, reason=reason, confidence=confidence, status="active")
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update_active(self, weak_concept_id: str, *, reason: str, confidence: float) -> WeakConcept:
        model = await self._session.get(WeakConceptModel, weak_concept_id)
        model.reason = reason
        model.confidence = confidence
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def resolve(self, weak_concept_id: str) -> WeakConcept:
        model = await self._session.get(WeakConceptModel, weak_concept_id)
        model.status = "resolved"
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_active_by_user_and_concept(self, user_id: str, concept_id: str) -> WeakConcept | None:
        stmt = select(WeakConceptModel).where(
            WeakConceptModel.user_id == user_id,
            WeakConceptModel.concept_id == concept_id,
            WeakConceptModel.status == "active",
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_active_by_user(self, user_id: str) -> list[WeakConcept]:
        stmt = select(WeakConceptModel).where(
            WeakConceptModel.user_id == user_id, WeakConceptModel.status == "active"
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
