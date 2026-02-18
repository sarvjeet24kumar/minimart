"""
Authentication Endpoints

"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_tenant_id
from app.core.rate_limit import RateLimit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    OTPResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    ResendOtpRequest,
    SignupRequest,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import ChangePasswordRequest
from app.services.auth_service import AuthService

router = APIRouter(dependencies=[Depends(RateLimit(settings.RATE_LIMIT_AUTH, scope="auth"))])
security = HTTPBearer(auto_error=True)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    tenant_id: Annotated[UUID | None, Depends(get_tenant_id)] = None,
):
    """
    Authenticate user and return JWT tokens.
    """
    auth_service = AuthService(db)
    return await auth_service.login(
        **data.model_dump(), tenant_id=tenant_id, background_tasks=background_tasks
    )


@router.post(
    "/signup",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    data: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
):
    """
    Register a new user account.
    """
    auth_service = AuthService(db)
    return await auth_service.signup(
        **data.model_dump(),
        tenant_id=tenant_id,
        background_tasks=background_tasks,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    data: LogoutRequest,
    current_user: Annotated["User", Depends(get_current_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Logout user by blacklisting both access and refresh tokens.
    """
    auth_service = AuthService(db)
    access_token = credentials.credentials
    return await auth_service.logout(access_token, data.refresh_token)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_email(
    data: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
):
    """
    Verify email address using OTP.
    """
    auth_service = AuthService(db)
    return await auth_service.verify_email(**data.model_dump(), tenant_id=tenant_id)


@router.post(
    "/resend-otp",
    response_model=OTPResponse,
    status_code=status.HTTP_200_OK,
)
async def resend_otp(
    data: ResendOtpRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    tenant_id: Annotated[UUID, Depends(get_tenant_id)],
):
    """
    Resend OTP for email verification.
    """
    auth_service = AuthService(db)
    return await auth_service.send_verification_otp(data.email, tenant_id, background_tasks)


@router.post(
    "/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_tokens(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Refresh access and refresh tokens.
    """
    auth_service = AuthService(db)
    return await auth_service.refresh_tokens(data.refresh_token)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Change current user's password.
    """
    auth_service = AuthService(db)
    return await auth_service.change_password(
        current_user, data.current_password, data.new_password
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def forgot_password(
    data: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
    tenant_id: Annotated[UUID | None, Depends(get_tenant_id)] = None,
):
    """
    Request a password reset link via email.
    """
    auth_service = AuthService(db)
    return await auth_service.forgot_password(data.email, tenant_id, background_tasks)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_password(
    data: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Reset password using a valid reset token.
    """
    auth_service = AuthService(db)
    return await auth_service.reset_password(
        data.token, data.new_password, data.confirm_password
    )

