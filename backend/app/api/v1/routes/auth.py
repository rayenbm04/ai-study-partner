from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_auth_service, get_current_user
from app.api.v1.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.domain.entities.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)) -> UserResponse:
    user = await service.register(
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password,
        firstname=payload.firstname,
        lastname=payload.lastname,
        pseudo=payload.pseudo,
        date_of_birth=payload.date_of_birth,
        school_name=payload.school_name,
    )
    return UserResponse.from_entity(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    user = await service.authenticate(email=payload.email, password=payload.password)
    tokens = await service.issue_token_pair(user)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    tokens = await service.refresh(payload.refresh_token)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)) -> None:
    await service.logout(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_entity(current_user)
