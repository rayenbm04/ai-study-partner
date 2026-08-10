from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.school import School, SchoolClass
from app.domain.repositories.school_repository import SchoolRepository
from app.infrastructure.db.models.school import SchoolClassModel, SchoolModel


def _school(model: SchoolModel) -> School:
    return School(
        id=model.id, name=model.name, country=model.country, city=model.city, status=model.status,
        created_at=model.created_at,
    )


def _school_class(model: SchoolClassModel) -> SchoolClass:
    return SchoolClass(
        id=model.id, school_id=model.school_id, level=model.level, label=model.label, created_at=model.created_at
    )


class SqlAlchemySchoolRepository(SchoolRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search(self, query: str, *, limit: int = 20) -> list[School]:
        stmt = select(SchoolModel).order_by(SchoolModel.name).limit(limit)
        if query:
            stmt = stmt.where(SchoolModel.name.ilike(f"%{query}%"))
        models = (await self._session.execute(stmt)).scalars().all()
        return [_school(m) for m in models]

    async def get_by_id(self, school_id: str) -> School | None:
        model = await self._session.get(SchoolModel, school_id)
        return _school(model) if model else None

    async def create(self, *, name: str, country: str | None, city: str | None) -> School:
        model = SchoolModel(name=name, country=country, city=city)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _school(model)

    async def list_classes(self, school_id: str) -> list[SchoolClass]:
        stmt = (
            select(SchoolClassModel)
            .where(SchoolClassModel.school_id == school_id)
            .order_by(SchoolClassModel.level, SchoolClassModel.label)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_school_class(m) for m in models]

    async def get_class(self, class_id: str) -> SchoolClass | None:
        model = await self._session.get(SchoolClassModel, class_id)
        return _school_class(model) if model else None

    async def create_class(self, *, school_id: str, level: str, label: str) -> SchoolClass:
        model = SchoolClassModel(school_id=school_id, level=level, label=label)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _school_class(model)
