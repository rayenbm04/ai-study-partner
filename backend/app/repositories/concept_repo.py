from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.concept import Concept
from app.domain.repositories.concept_repository import ConceptRepository
from app.infrastructure.db.models.concept import ConceptModel
from app.infrastructure.db.models.concept_prerequisite import ConceptPrerequisiteModel


def _to_entity(model: ConceptModel) -> Concept:
    return Concept(
        id=model.id,
        subject_id=model.subject_id,
        name=model.name,
        description=model.description,
        parent_concept_id=model.parent_concept_id,
    )


class SqlAlchemyConceptRepository(ConceptRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_by_subject(self, subject_id: str) -> list[Concept]:
        stmt = select(ConceptModel).where(ConceptModel.subject_id == subject_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]

    async def get_by_subject_and_name(self, subject_id: str, name: str) -> Concept | None:
        stmt = select(ConceptModel).where(ConceptModel.subject_id == subject_id, ConceptModel.name == name)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(self, *, subject_id: str, name: str, description: str | None) -> Concept:
        model = ConceptModel(subject_id=subject_id, name=name, description=description)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def add_prerequisite(self, *, concept_id: str, prerequisite_id: str) -> None:
        if concept_id == prerequisite_id:
            return  # a concept can't require itself
        self._session.add(ConceptPrerequisiteModel(concept_id=concept_id, prerequisite_id=prerequisite_id))
        await self._session.flush()
