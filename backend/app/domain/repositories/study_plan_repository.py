from abc import ABC, abstractmethod
from datetime import date

from app.domain.entities.study_plan import StudyPlan, StudyPlanItem, StudyPlanItemDraft


class StudyPlanRepository(ABC):
    @abstractmethod
    async def create(
        self, *, user_id: str, name: str, exam_date: date | None, daily_minutes_available: int
    ) -> StudyPlan: ...

    @abstractmethod
    async def bulk_create_items(
        self, *, study_plan_id: str, drafts: list[StudyPlanItemDraft]
    ) -> list[StudyPlanItem]: ...

    @abstractmethod
    async def get_by_id(self, study_plan_id: str) -> StudyPlan | None: ...

    @abstractmethod
    async def list_items(self, study_plan_id: str) -> list[StudyPlanItem]: ...

    @abstractmethod
    async def get_item_by_id(self, item_id: str) -> StudyPlanItem | None: ...

    @abstractmethod
    async def update_item_status(self, item_id: str, *, status: str) -> StudyPlanItem: ...

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> None:
        """Used by account reset — study_plans is keyed only by user_id (no
        subject_id), so it isn't reachable by cascading a subject delete."""
        ...
