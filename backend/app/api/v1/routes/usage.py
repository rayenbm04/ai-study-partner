from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_usage_service
from app.api.v1.schemas.usage import UsageSummaryResponse
from app.domain.entities.user import User
from app.services.usage_service import UsageService

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/me", response_model=UsageSummaryResponse)
async def get_my_usage(
    current_user: User = Depends(get_current_user),
    service: UsageService = Depends(get_usage_service),
) -> UsageSummaryResponse:
    summary = await service.get_usage_summary(current_user.id)
    return UsageSummaryResponse.from_domain(summary)
