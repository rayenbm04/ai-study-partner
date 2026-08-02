from fastapi import APIRouter, Depends

from app.api.v1.deps import get_analytics_service, get_current_user
from app.api.v1.schemas.analytics import OverviewAnalyticsResponse, SubjectAnalyticsResponse
from app.domain.entities.user import User
from app.services.analytics_engine.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewAnalyticsResponse)
async def get_overview(
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> OverviewAnalyticsResponse:
    overview = await service.get_overview(user_id=current_user.id)
    return OverviewAnalyticsResponse.from_domain(overview)


@router.get("/subjects/{subject_id}", response_model=SubjectAnalyticsResponse)
async def get_subject_analytics(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> SubjectAnalyticsResponse:
    analytics = await service.get_subject_analytics(user_id=current_user.id, subject_id=subject_id)
    return SubjectAnalyticsResponse.from_domain(analytics)
