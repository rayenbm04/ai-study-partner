from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.entities.study_plan import StudyPlan, StudyPlanItem


class StudyPlanGenerateRequest(BaseModel):
    name: str
    subject_ids: list[str] = Field(min_length=1)
    exam_date: date | None = None
    daily_minutes_available: int = Field(default=30, gt=0)


class StudyPlanItemResponse(BaseModel):
    id: str
    subject_id: str
    concept_id: str | None
    scheduled_date: date
    activity_type: str
    duration_minutes: int
    status: str

    @classmethod
    def from_entity(cls, item: StudyPlanItem) -> "StudyPlanItemResponse":
        return cls(
            id=item.id,
            subject_id=item.subject_id,
            concept_id=item.concept_id,
            scheduled_date=item.scheduled_date,
            activity_type=item.activity_type,
            duration_minutes=item.duration_minutes,
            status=item.status,
        )


class StudyPlanResponse(BaseModel):
    id: str
    name: str
    exam_date: date | None
    daily_minutes_available: int
    status: str
    created_at: datetime
    items: list[StudyPlanItemResponse] = []

    @classmethod
    def from_entity(cls, plan: StudyPlan, items: list[StudyPlanItem]) -> "StudyPlanResponse":
        return cls(
            id=plan.id,
            name=plan.name,
            exam_date=plan.exam_date,
            daily_minutes_available=plan.daily_minutes_available,
            status=plan.status,
            created_at=plan.created_at,
            items=[StudyPlanItemResponse.from_entity(item) for item in items],
        )


class StudyPlanItemUpdateRequest(BaseModel):
    status: str
