from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.study_plan import StudyPlan, StudyPlanItem, StudyPlanItemDraft
from app.domain.repositories.study_plan_repository import StudyPlanRepository
from app.infrastructure.db.models.study_plan import StudyPlanModel
from app.infrastructure.db.models.study_plan_item import StudyPlanItemModel


def _plan_to_entity(model: StudyPlanModel) -> StudyPlan:
    return StudyPlan(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        exam_date=model.exam_date,
        daily_minutes_available=model.daily_minutes_available,
        status=model.status,
        created_at=model.created_at,
    )


def _item_to_entity(model: StudyPlanItemModel) -> StudyPlanItem:
    return StudyPlanItem(
        id=model.id,
        study_plan_id=model.study_plan_id,
        subject_id=model.subject_id,
        concept_id=model.concept_id,
        scheduled_date=model.scheduled_date,
        activity_type=model.activity_type,
        duration_minutes=model.duration_minutes,
        status=model.status,
    )


class SqlAlchemyStudyPlanRepository(StudyPlanRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, *, user_id, name, exam_date, daily_minutes_available) -> StudyPlan:
        model = StudyPlanModel(user_id=user_id, name=name, exam_date=exam_date, daily_minutes_available=daily_minutes_available)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _plan_to_entity(model)

    async def bulk_create_items(self, *, study_plan_id: str, drafts: list[StudyPlanItemDraft]) -> list[StudyPlanItem]:
        models = [
            StudyPlanItemModel(
                study_plan_id=study_plan_id,
                subject_id=draft.subject_id,
                concept_id=draft.concept_id,
                scheduled_date=draft.scheduled_date,
                activity_type=draft.activity_type,
                duration_minutes=draft.duration_minutes,
            )
            for draft in drafts
        ]
        self._session.add_all(models)
        await self._session.flush()
        for model in models:
            await self._session.refresh(model)
        return [_item_to_entity(m) for m in models]

    async def get_by_id(self, study_plan_id: str) -> StudyPlan | None:
        model = await self._session.get(StudyPlanModel, study_plan_id)
        return _plan_to_entity(model) if model else None

    async def list_items(self, study_plan_id: str) -> list[StudyPlanItem]:
        stmt = select(StudyPlanItemModel).where(StudyPlanItemModel.study_plan_id == study_plan_id)
        models = (await self._session.execute(stmt)).scalars().all()
        return [_item_to_entity(m) for m in models]

    async def get_item_by_id(self, item_id: str) -> StudyPlanItem | None:
        model = await self._session.get(StudyPlanItemModel, item_id)
        return _item_to_entity(model) if model else None

    async def update_item_status(self, item_id: str, *, status: str) -> StudyPlanItem:
        model = await self._session.get(StudyPlanItemModel, item_id)
        model.status = status
        await self._session.flush()
        await self._session.refresh(model)
        return _item_to_entity(model)

    async def delete_all_for_user(self, user_id: str) -> None:
        await self._session.execute(delete(StudyPlanModel).where(StudyPlanModel.user_id == user_id))
        await self._session.flush()
