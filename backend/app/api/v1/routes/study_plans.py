from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_current_user, get_planning_service
from app.api.v1.schemas.study_plan import (
    StudyPlanGenerateRequest,
    StudyPlanItemResponse,
    StudyPlanItemUpdateRequest,
    StudyPlanResponse,
)
from app.domain.entities.user import User
from app.services.planning_engine.planning_service import PlanningService

router = APIRouter(tags=["study-plans"])


@router.post("/study-plans", response_model=StudyPlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_study_plan(
    body: StudyPlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> StudyPlanResponse:
    plan = await service.generate(
        user_id=current_user.id,
        name=body.name,
        subject_ids=body.subject_ids,
        exam_date=body.exam_date,
        daily_minutes_available=body.daily_minutes_available,
    )
    items = await service.get_items(current_user.id, plan.id)
    return StudyPlanResponse.from_entity(plan, items)


@router.get("/study-plans/{study_plan_id}", response_model=StudyPlanResponse)
async def get_study_plan(
    study_plan_id: str,
    current_user: User = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> StudyPlanResponse:
    plan = await service.get_owned(current_user.id, study_plan_id)
    items = await service.get_items(current_user.id, study_plan_id)
    return StudyPlanResponse.from_entity(plan, items)


@router.patch("/study-plan-items/{item_id}", response_model=StudyPlanItemResponse)
async def update_study_plan_item(
    item_id: str,
    body: StudyPlanItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> StudyPlanItemResponse:
    item = await service.update_item_status(current_user.id, item_id, status=body.status)
    return StudyPlanItemResponse.from_entity(item)
