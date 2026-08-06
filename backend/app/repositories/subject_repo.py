from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SubjectNotFoundError
from app.domain.entities.subject import Subject
from app.domain.repositories.subject_repository import SubjectRepository
from app.infrastructure.db.models.subject import SubjectModel


def _to_entity(model: SubjectModel) -> Subject:
    return Subject(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        description=model.description,
        color=model.color,
        icon=model.icon,
        created_at=model.created_at,
        archived_at=model.archived_at,
        curriculum_subject_id=model.curriculum_subject_id,
    )


class SqlAlchemySubjectRepository(SubjectRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_by_user(self, user_id: str, *, include_archived: bool = False) -> list[Subject]:
        stmt = select(SubjectModel).where(SubjectModel.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(SubjectModel.archived_at.is_(None))
        stmt = stmt.order_by(SubjectModel.created_at.desc())
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]

    async def get_by_id(self, subject_id: str) -> Subject | None:
        model = await self._session.get(SubjectModel, subject_id)
        return _to_entity(model) if model else None

    async def get_by_user_and_name(self, user_id: str, name: str) -> Subject | None:
        stmt = select(SubjectModel).where(
            SubjectModel.user_id == user_id, SubjectModel.name == name, SubjectModel.archived_at.is_(None)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(
        self,
        *,
        user_id: str,
        name: str,
        description: str | None,
        color: str | None,
        icon: str | None,
        curriculum_subject_id: str | None = None,
    ) -> Subject:
        model = SubjectModel(
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            curriculum_subject_id=curriculum_subject_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, subject_id: str, **fields) -> Subject:
        model = await self._session.get(SubjectModel, subject_id)
        if model is None:
            raise SubjectNotFoundError(subject_id)
        for key, value in fields.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def archive(self, subject_id: str) -> None:
        model = await self._session.get(SubjectModel, subject_id)
        if model is None:
            raise SubjectNotFoundError(subject_id)
        model.archived_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def delete_all_for_user(self, user_id: str) -> None:
        await self._session.execute(delete(SubjectModel).where(SubjectModel.user_id == user_id))
        await self._session.flush()
