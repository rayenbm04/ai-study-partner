"""Bulk apply/remove of a curriculum node's subjects as a 'pack' (see
SubjectPackService for why this isn't a stored entity), plus listing which
packs the current user already has applied."""
from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_subject_pack_service
from app.api.v1.schemas.subject_pack import (
    AppliedSubjectPackResponse,
    SubjectPackApplyResponse,
    SubjectPackRemoveResponse,
    SubjectPackRequest,
)
from app.domain.entities.user import User
from app.services.subject_pack_service import SubjectPackService

router = APIRouter(prefix="/subject-packs", tags=["subject-packs"])


@router.get("", response_model=list[AppliedSubjectPackResponse])
async def list_applied_packs(
    current_user: User = Depends(get_current_user),
    service: SubjectPackService = Depends(get_subject_pack_service),
) -> list[AppliedSubjectPackResponse]:
    packs = await service.list_applied(current_user.id)
    return [AppliedSubjectPackResponse.from_entity(p) for p in packs]


@router.post("/apply", response_model=SubjectPackApplyResponse)
async def apply_pack(
    payload: SubjectPackRequest,
    current_user: User = Depends(get_current_user),
    service: SubjectPackService = Depends(get_subject_pack_service),
) -> SubjectPackApplyResponse:
    result = await service.apply(current_user.id, academic_level_id=payload.academic_level_id, section_id=payload.section_id)
    return SubjectPackApplyResponse.from_result(result)


@router.post("/remove", response_model=SubjectPackRemoveResponse)
async def remove_pack(
    payload: SubjectPackRequest,
    current_user: User = Depends(get_current_user),
    service: SubjectPackService = Depends(get_subject_pack_service),
) -> SubjectPackRemoveResponse:
    removed_count = await service.remove(
        current_user.id, academic_level_id=payload.academic_level_id, section_id=payload.section_id
    )
    return SubjectPackRemoveResponse(removed_count=removed_count)
