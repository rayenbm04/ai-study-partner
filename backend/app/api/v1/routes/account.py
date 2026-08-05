from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_account_service, get_current_user
from app.domain.entities.user import User
from app.services.account_service import AccountService

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_account(
    current_user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> None:
    await service.reset(current_user.id)
