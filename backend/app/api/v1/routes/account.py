from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_account_service, get_current_user
from app.api.v1.schemas.account import SetClasseRequest
from app.api.v1.schemas.auth import UpdateProfileRequest, UserResponse
from app.domain.entities.user import User
from app.services.account_service import AccountService

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_account(
    current_user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> None:
    await service.reset(current_user.id)


@router.patch("/classe", response_model=UserResponse)
async def set_classe(
    payload: SetClasseRequest,
    current_user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> UserResponse:
    user = await service.set_classe(
        current_user.id, academic_level_id=payload.academic_level_id, section_id=payload.section_id
    )
    return UserResponse.from_entity(user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> UserResponse:
    user = await service.update_profile(current_user.id, firstname=payload.firstname, lastname=payload.lastname)
    return UserResponse.from_entity(user)
