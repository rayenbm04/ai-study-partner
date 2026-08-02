from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, get_progress_service
from app.api.v1.schemas.progress import ConceptMasteryResponse, WeakConceptResponse
from app.domain.entities.user import User
from app.services.progress_engine.progress_service import ProgressService

router = APIRouter(tags=["progress"])


@router.get("/subjects/{subject_id}/progress", response_model=list[ConceptMasteryResponse])
async def get_progress(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> list[ConceptMasteryResponse]:
    nodes = await service.get_progress(user_id=current_user.id, subject_id=subject_id)
    return [ConceptMasteryResponse.from_domain(node) for node in nodes]


@router.get("/subjects/{subject_id}/weak-concepts", response_model=list[WeakConceptResponse])
async def get_weak_concepts(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
) -> list[WeakConceptResponse]:
    weak_concepts = await service.get_weak_concepts(user_id=current_user.id, subject_id=subject_id)
    return [WeakConceptResponse.from_entity(w) for w in weak_concepts]
