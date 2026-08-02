from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_current_user, get_subject_service
from app.api.v1.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.domain.entities.user import User
from app.services.subject_service import SubjectService

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectResponse])
async def list_subjects(
    current_user: User = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
) -> list[SubjectResponse]:
    subjects = await service.list_for_user(current_user.id)
    return [SubjectResponse.from_entity(s) for s in subjects]


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    current_user: User = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
) -> SubjectResponse:
    subject = await service.create(
        current_user.id,
        name=payload.name,
        description=payload.description,
        color=payload.color,
        icon=payload.icon,
    )
    return SubjectResponse.from_entity(subject)


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
) -> SubjectResponse:
    subject = await service.get_owned(current_user.id, subject_id)
    return SubjectResponse.from_entity(subject)


@router.patch("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: str,
    payload: SubjectUpdate,
    current_user: User = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
) -> SubjectResponse:
    subject = await service.update(current_user.id, subject_id, **payload.model_dump(exclude_unset=True))
    return SubjectResponse.from_entity(subject)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_subject(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
) -> None:
    await service.archive(current_user.id, subject_id)
