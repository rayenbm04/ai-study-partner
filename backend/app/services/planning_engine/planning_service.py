"""Generates and manages study plans — orchestrates scheduler.py (pure
ranking/distribution) around evidence already produced by the progress
engine (mastery scores, weak-concept flags) and persists the result via
StudyPlanRepository.

Deliberately does not track "study sessions" as a separate concept from
plan items, and does not maintain a standing "revision schedule" table —
docs/ARCHITECTURE.md's Planning Engine API contract only lists plan
creation/read and per-item status updates, and auto-logging real study
sessions would mean hooking into every other engine (flashcard reviews,
quiz attempts, chat) just to feed this one. A plan item's status
(pending/done/skipped) is set explicitly by the student instead.
"""
from datetime import date

from app.core.exceptions import (
    EmptyStudyPlanError,
    InvalidStudyPlanItemStatusError,
    StudyPlanItemNotFoundError,
    StudyPlanNotFoundError,
)
from app.domain.entities.study_plan import STUDY_PLAN_ITEM_STATUSES, StudyPlan, StudyPlanItem
from app.domain.repositories.study_plan_repository import StudyPlanRepository
from app.services.planning_engine import scheduler as scheduler_module
from app.services.planning_engine.scheduler import build_plan_items, rank_concepts
from app.services.progress_engine.mastery import flatten_leaves
from app.services.progress_engine.progress_service import ProgressService
from app.services.subject_service import SubjectService


class PlanningService:
    def __init__(
        self,
        *,
        study_plan_repo: StudyPlanRepository,
        subject_service: SubjectService,
        progress_service: ProgressService,
        default_session_minutes: int = scheduler_module.DEFAULT_SESSION_MINUTES,
        default_plan_days: int = scheduler_module.DEFAULT_PLAN_DAYS,
    ):
        self._plans = study_plan_repo
        self._subjects = subject_service
        self._progress = progress_service
        self._default_session_minutes = default_session_minutes
        self._default_plan_days = default_plan_days

    async def generate(
        self,
        *,
        user_id: str,
        name: str,
        subject_ids: list[str],
        exam_date: date | None,
        daily_minutes_available: int,
        start_date: date | None = None,
    ) -> StudyPlan:
        for subject_id in subject_ids:
            await self._subjects.get_owned(user_id, subject_id)

        concepts: list[tuple[str, str, float | None]] = []
        weak_concept_ids: set[str] = set()
        for subject_id in subject_ids:
            rollup = await self._progress.get_progress(user_id=user_id, subject_id=subject_id)
            for leaf in flatten_leaves(rollup):
                concepts.append((leaf.concept_id, subject_id, leaf.mastery_score))
            weak = await self._progress.get_weak_concepts(user_id=user_id, subject_id=subject_id)
            weak_concept_ids.update(w.concept_id for w in weak)

        if not concepts:
            raise EmptyStudyPlanError()

        priorities = rank_concepts(concepts, weak_concept_ids)
        drafts = build_plan_items(
            priorities=priorities,
            start_date=start_date or date.today(),
            exam_date=exam_date,
            daily_minutes_available=daily_minutes_available,
            session_minutes=self._default_session_minutes,
            default_plan_days=self._default_plan_days,
        )

        plan = await self._plans.create(
            user_id=user_id, name=name, exam_date=exam_date, daily_minutes_available=daily_minutes_available
        )
        await self._plans.bulk_create_items(study_plan_id=plan.id, drafts=drafts)
        return plan

    async def get_owned(self, user_id: str, study_plan_id: str) -> StudyPlan:
        plan = await self._plans.get_by_id(study_plan_id)
        if plan is None or plan.user_id != user_id:
            raise StudyPlanNotFoundError(study_plan_id)
        return plan

    async def get_items(self, user_id: str, study_plan_id: str) -> list[StudyPlanItem]:
        await self.get_owned(user_id, study_plan_id)
        return await self._plans.list_items(study_plan_id)

    async def update_item_status(self, user_id: str, item_id: str, *, status: str) -> StudyPlanItem:
        if status not in STUDY_PLAN_ITEM_STATUSES:
            raise InvalidStudyPlanItemStatusError(status, STUDY_PLAN_ITEM_STATUSES)
        item = await self._plans.get_item_by_id(item_id)
        if item is None:
            raise StudyPlanItemNotFoundError(item_id)
        await self.get_owned(user_id, item.study_plan_id)  # ownership check via the parent plan
        return await self._plans.update_item_status(item_id, status=status)
