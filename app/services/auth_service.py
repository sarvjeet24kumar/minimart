"""
Authentication Service

"""

import hmac
from datetime import datetime
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks
from jose import JWTError, jwt
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_password_reset_token,
    decode_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.core.time import get_now
from app.exceptions import (
    ConflictException,
    EmailNotVerifiedException,
    ForbiddenException,
    NotFoundException,
    TenantInactiveException,
    UnauthorizedException,
    ValidationException,
)
from app.exceptions.base import MiniMartException
from app.models.tenant import Tenant
from app.models.token_blacklist import BlacklistedToken
from app.models.user import User
from app.schemas.auth import LoginResponse
from app.services.email_service import EmailService
from app.services.redis_service import RedisService
from app.utils.password import validate_password_strength
from app.websocket.manager import manager

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(
        self,
        email: str,
        password: str,
        tenant_id: UUID | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> LoginResponse:
        """
        Authenticate user and return tokens.
        """
        email = email.strip().lower()
        if not tenant_id:

            result = await self.db.execute(
                select(User).where(
                    and_(
                        User.email == email,
                        User.tenant_id == tenant_id,
                        User.role == UserRole.SUPER_ADMIN,
                    )
                )
            )
        else:
            result = await self.db.execute(
                select(User).where(
                    and_(User.email == email, User.tenant_id == tenant_id)
                )
            )
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException("Invalid email or password")

        if not verify_password(password, user.password):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise ForbiddenException("User account is inactive")

        if not user.is_email_verified:

            await self.send_verification_otp(email, tenant_id, background_tasks)
            raise EmailNotVerifiedException(
                "Please verify your email before logging in. A new OTP has been sent."
            )

        if user.tenant_id:
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == user.tenant_id)
            )
            tenant = result.scalar_one_or_none()

            if not tenant or not tenant.is_active:
                raise TenantInactiveException()

        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role.value,
            email=user.email,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )

        return LoginResponse(access_token=access_token, refresh_token=refresh_token)

    async def send_verification_otp(
        self,
        email: str,
        tenant_id: UUID | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        """
        Send OTP for email verification scoped by tenant.
        """
        email = email.strip().lower()
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.email == email,
                    User.tenant_id == tenant_id,
                    User.deleted_at.is_(None),
                )
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            return

        if user.is_email_verified:
            raise MiniMartException(
                status_code=400,
                code="ALREADY_VERIFIED",
                message="Account is already verified.",
            )

        otp = generate_otp()

        expire_seconds = settings.OTP_EXPIRE_MINUTES * 60
        await RedisService.store_otp(email, otp, expire_seconds, tenant_id)

        if background_tasks:
            background_tasks.add_task(EmailService.send_otp_email, email, otp)
        else:
            await EmailService.send_otp_email(email, otp)

    async def verify_email(self, email: str, otp: str, tenant_id: UUID) -> bool:
        """
        Verify email with OTP scoped by tenant.
        """
        result = await self.db.execute(
            select(User).where(and_(User.email == email, User.tenant_id == tenant_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("User not found")

        if user.is_email_verified:
            raise MiniMartException(
                status_code=400,
                code="ALREADY_VERIFIED",
                message="Account is already verified.",
            )

        stored_otp = await RedisService.get_otp(email, tenant_id)

        if not stored_otp:
            raise ValidationException("OTP has expired. Please request a new one.")

        if not hmac.compare_digest(stored_otp, otp):
            raise ValidationException("Invalid OTP")

        user.is_email_verified = True
        user.is_active = True
        await self.db.commit()

        await RedisService.delete_otp(email, tenant_id)

        return True

    async def signup(
        self,
        email: str,
        username: str,
        first_name: str,
        last_name: str,
        password: str,
        tenant_id: UUID | None = None,
        background_tasks: Optional["BackgroundTasks"] = None,
    ) -> bool:
        """
        Register a new user with email verification.
        """
        validate_password_strength(password)

        if tenant_id:
            result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = result.scalar_one_or_none()
            if not tenant:
                raise NotFoundException("Tenant not found")
            if not tenant.is_active:
                raise TenantInactiveException()

        result = await self.db.execute(
            select(User).where(and_(User.email == email, User.tenant_id == tenant_id))
        )
        if result.scalar_one_or_none():
            raise ConflictException("Email already registered in this tenant")

        result = await self.db.execute(
            select(User).where(
                and_(User.username == username, User.tenant_id == tenant_id)
            )
        )
        if result.scalar_one_or_none():
            raise ConflictException("Username already exist")
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=hash_password(password),
            tenant_id=tenant_id,
            role=UserRole.USER,
            is_email_verified=False,
            is_active=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        await self.send_verification_otp(email, tenant_id, background_tasks)
        return True

    async def logout(
        self,
        access_token: str,
        refresh_token: str,
    ) -> None:
        """
        Logout user by blacklisting both access and refresh tokens.
        """
        try:
            access_payload = decode_token(access_token)
        except JWTError as e:
            raise UnauthorizedException("Invalid access token") from e

        try:
            refresh_payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedException("Invalid refresh token")

        access_jti = access_payload.get("jti")
        access_exp = access_payload.get("exp")
        if access_jti and access_exp:
            ttl = int(access_exp - get_now().timestamp())
            if ttl > 0:
                await RedisService.blacklist_access_token(access_jti, ttl)

        refresh_jti = refresh_payload.get("jti")
        refresh_exp = refresh_payload.get("exp")
        user_id = refresh_payload.get("sub")

        if refresh_jti and refresh_exp:
            result = await self.db.execute(
                select(BlacklistedToken).where(BlacklistedToken.token_id == refresh_jti)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                expires_at = datetime.fromtimestamp(
                    refresh_payload["exp"], tz=ZoneInfo(settings.TIMEZONE)
                )

                blacklisted = BlacklistedToken(
                    token_id=refresh_jti,
                    user_id=user_id,
                    expires_at=expires_at,
                )
                self.db.add(blacklisted)
                await self.db.commit()
        await manager.disconnect_all_for_user(str(user_id))

    async def refresh_tokens(self, refresh_token: str) -> tuple[str, str]:

        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError:
            raise UnauthorizedException("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")

        token_id = payload.get("jti")
        result = await self.db.execute(
            select(BlacklistedToken).where(BlacklistedToken.token_id == token_id)
        )
        if result.scalar_one_or_none():
            raise UnauthorizedException("Token has been revoked")

        user_id = payload.get("sub")
        result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role.value,
            email=user.email,
        )

        return access_token, refresh_token

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> bool:
        """
        Change user's password with strength validation.
        """
        if not verify_password(current_password, user.password):
            raise ValidationException("Current password is incorrect")

        if verify_password(new_password, user.password):
            raise MiniMartException(
                status_code=400,
                code="PASSWORD_SAME",
                message="New password must be different from your current password.",
            )

        validate_password_strength(new_password)

        user.password = hash_password(new_password)
        await self.db.commit()

        return True

    async def forgot_password(
        self,
        email: str,
        tenant_id: UUID | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        """
        Request password reset. Sends email with reset link.
        """
        email = email.strip().lower()
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.email == email,
                    User.tenant_id == tenant_id,
                    User.deleted_at.is_(None),
                )
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        token = create_password_reset_token(user.id, user.tenant_id)
        payload = decode_token(token)
        jti = payload.get("jti")

        await RedisService.store_password_reset_jti(jti, str(user.id), 900)
        reset_url = f"{settings.INVITATION_BASE_URL.rsplit('/', 1)[0]}/reset-password?token={token}"

        if background_tasks:
            background_tasks.add_task(
                EmailService.send_password_reset_email, user.email, reset_url
            )
        else:
            await EmailService.send_password_reset_email(user.email, reset_url)

    async def reset_password(
        self, token: str, new_password: str, confirm_password: str
    ) -> bool:
        """
        Reset password using a valid reset token.
        """
        if new_password != confirm_password:
            raise MiniMartException(
                status_code=400,
                code="PASSWORD_MISMATCH",
                message="Passwords do not match.",
                details={"confirm_password": ["Must match new_password."]},
            )

        validate_password_strength(new_password)
        try:
            payload = decode_password_reset_token(token)
        except JWTError as e:
            raise MiniMartException(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Password reset token is invalid or has expired.",
            ) from e

        jti = payload.get("jti")
        user_id = payload.get("sub")

        stored_user_id = await RedisService.validate_password_reset_jti(jti)
        if not stored_user_id:
            raise MiniMartException(
                status_code=400,
                code="INVALID_RESET_TOKEN",
                message="Password reset token has already been used or has expired.",
            )

        result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("User not found")

        user.password = hash_password(new_password)
        await self.db.commit()

        await RedisService.delete_password_reset_jti(jti)

        return True
