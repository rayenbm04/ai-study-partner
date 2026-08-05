from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_summary_service
from app.api.v1.schemas.summary import SummaryRequest, SummaryResponse, SummaryType
from app.domain.entities.user import User
from app.services.summary_engine.summary_service import SummaryService

router = APIRouter(tags=["summaries"])


@router.post("/subjects/{subject_id}/summaries", response_model=SummaryResponse)
async def generate_summary(
    subject_id: str,
    body: SummaryRequest,
    current_user: User = Depends(get_current_user),
    service: SummaryService = Depends(get_summary_service),
) -> SummaryResponse:
    summary = await service.generate(
        user_id=current_user.id, subject_id=subject_id, document_id=body.document_id, summary_type=body.summary_type
    )
    return SummaryResponse.from_entity(summary)


@router.get("/documents/{document_id}/summary", response_model=SummaryResponse)
async def get_summary(
    document_id: str,
    summary_type: SummaryType,
    current_user: User = Depends(get_current_user),
    service: SummaryService = Depends(get_summary_service),
) -> SummaryResponse:
    summary = await service.get_cached(user_id=current_user.id, document_id=document_id, summary_type=summary_type)
    return SummaryResponse.from_entity(summary)


@router.get("/documents/{document_id}/summaries", response_model=list[SummaryResponse])
async def list_summaries(
    document_id: str,
    current_user: User = Depends(get_current_user),
    service: SummaryService = Depends(get_summary_service),
) -> list[SummaryResponse]:
    summaries = await service.list_for_document(user_id=current_user.id, document_id=document_id)
    return [SummaryResponse.from_entity(s) for s in summaries]
