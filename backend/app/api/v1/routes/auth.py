from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_auth_service, get_current_user
from app.api.v1.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
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
        school_id=payload.school_id,
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


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(payload: VerifyEmailRequest, service: AuthService = Depends(get_auth_service)) -> UserResponse:
    user = await service.verify_email(payload.token)
    return UserResponse.from_entity(user)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(payload: ForgotPasswordRequest, service: AuthService = Depends(get_auth_service)) -> None:
    await service.request_password_reset(payload.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, service: AuthService = Depends(get_auth_service)) -> None:
    await service.reset_password(
        raw_token=payload.token, new_password=payload.new_password, confirm_new_password=payload.confirm_new_password
    )
