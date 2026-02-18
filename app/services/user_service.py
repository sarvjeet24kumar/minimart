"""
User Service

Handles user management within a tenant (Tenant Admin operations).
"""

from uuid import UUID

from fastapi import BackgroundTasks, Response, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.common.enums import UserRole
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import generate_otp, hash_password
from app.core.time import get_now
from app.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserAdminResponse, UserCreate, UserResponse, UserUpdate
from app.services.email_service import EmailService
from app.services.redis_service import RedisService
from app.utils.password import validate_password_strength

logger = get_logger(__name__)


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _map_user_response(
        self, user: User, requester: User
    ) -> UserAdminResponse | UserResponse:
        """Helper to map user model to appropriate response schema based on role."""
        if requester.role in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
            return UserAdminResponse.model_validate(user)
        return UserResponse.model_validate(user)

    async def create_user(
        self,
        data: UserCreate,
        requester: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> UserAdminResponse:
        """
        Create a new user.
        Role and tenant are determined by the requester's role:
        - Super Admin creates Tenant Admins (no tenant scoping)
        - Tenant Admin creates Users (scoped to their tenant)
        """
        if requester.role == UserRole.SUPER_ADMIN:
            role = UserRole.TENANT_ADMIN
            target_tenant_id = data.tenant_id
        elif requester.role == UserRole.TENANT_ADMIN:
            role = UserRole.USER
            target_tenant_id = requester.tenant_id
        else:
            raise ForbiddenException("Only Admins can create users")

        validate_password_strength(data.password)

        if not target_tenant_id and role != UserRole.SUPER_ADMIN:
            raise ForbiddenException("Tenant ID is required")

        if target_tenant_id:
            tenant_result = await self.db.execute(
                select(Tenant).where(
                    Tenant.id == target_tenant_id,
                    Tenant.is_active,
                    Tenant.deleted_at.is_(None),
                )
            )
            if not tenant_result.scalar_one_or_none():
                raise NotFoundException("Tenant deleted or not found")

        result = await self.db.execute(
            select(User).where(
                and_(
                    User.tenant_id == target_tenant_id,
                    User.username == data.username,
                    User.is_active,
                    User.deleted_at.is_(None),
                )
            )
        )
        if result.scalar_one_or_none():
            raise ConflictException("Username already exists")

        # Check for existing email (scoped to tenant + globally for SuperAdmins)
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.email == data.email,
                    or_(User.tenant_id == target_tenant_id, User.tenant_id.is_(None)),
                )
            )
        )
        if result.scalar_one_or_none():
            raise ConflictException("Email already exists")

        hashed_password = hash_password(data.password)

        user = User(
            **data.model_dump(exclude={"password", "tenant_id"}),
            password=hashed_password,
            tenant_id=target_tenant_id,
            role=role,
            is_email_verified=False,
            is_active=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        otp = generate_otp()
        expire_seconds = settings.OTP_EXPIRE_MINUTES * 60
        await RedisService.store_otp(user.email, otp, expire_seconds, user.tenant_id)

        if background_tasks:
            background_tasks.add_task(EmailService.send_otp_email, user.email, otp)
        else:
            await EmailService.send_otp_email(user.email, otp)

        logger.info("User created successfully")
        return UserAdminResponse.model_validate(user)

    async def _get_user_with_access(self, user_id: UUID, requester: User) -> User:
        """Internal helper to get User model with access control."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("User not found")

        if requester.id == user.id:
            return user

        if requester.role == UserRole.SUPER_ADMIN:
            if user.role != UserRole.TENANT_ADMIN:
                raise ForbiddenException("Can only access Tenant Admin accounts")
            return user

        if requester.role == UserRole.TENANT_ADMIN:
            if user.tenant_id != requester.tenant_id:
                raise ForbiddenException("Can only access users in their own tenant")
            return user

        if requester.role == UserRole.USER:
            if user.tenant_id != requester.tenant_id:
                raise ForbiddenException("Can only access users in their own tenant")
            if not (user.is_active and not user.deleted_at):
                raise ForbiddenException("User account is inactive or deleted")
            return user

        raise ForbiddenException("Access denied")

    async def get_user(
        self, user_id: UUID, requester: User
    ) -> UserAdminResponse | UserResponse:
        """
        Get a user by ID with strict access control.
        """
        user = await self._get_user_with_access(user_id, requester)
        return self._map_user_response(user, requester)

    async def get_users_in_tenant(
        self,
        requester: User,
        pagination: PaginationParams,
        tenant_id: UUID | None = None,
    ) -> PaginatedResponse[UserAdminResponse | UserResponse]:
        """
        Get users based on requester context.
        """
        query = select(User).options(selectinload(User.tenant))
        count_query = select(func.count(User.id))

        filters = []
        # Regular users only see active/non-deleted users
        if requester.role == UserRole.USER:
            filters.extend([User.is_active.is_(True), User.deleted_at.is_(None)])

        if tenant_id:
            filters.append(User.tenant_id == tenant_id)
        else:
            # Super admins see tenant admins
            filters.append(User.role == UserRole.TENANT_ADMIN)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        result = await self.db.execute(
            query.offset(pagination.skip).limit(pagination.size)
        )
        users = result.scalars().all()

        items = [self._map_user_response(u, requester) for u in users]
        return PaginatedResponse(
            data=items, total=total, page=pagination.page, size=pagination.size
        )

    async def update_user(
        self, user_id: UUID, requester: User, data: UserUpdate
    ) -> UserAdminResponse | UserResponse:
        """
        Update a user with access control and restrictions.
        """
        user = await self._get_user_with_access(user_id, requester)

        # Regular users can only update their own account
        if requester.role == UserRole.USER and requester.id != user.id:
            raise ForbiddenException("Users can only update their own account")

        target_tenant_id = user.tenant_id
        update_data = data.model_dump(exclude_unset=True)
        if requester.id == user.id:
            if data.is_active is not None or (
                hasattr(data, "deleted_at") and data.deleted_at is not None
            ):
                raise ForbiddenException(
                    "You cannot modify your own account status (active/deleted)"
                )

        if data.username is not None and data.username != user.username:
            result = await self.db.execute(
                select(User).where(
                    and_(
                        User.tenant_id == target_tenant_id,
                        User.username == data.username,
                    )
                )
            )
            if result.scalar_one_or_none():
                raise ConflictException(f"Username already exists")
            user.username = data.username

        stmt = (
            update(User).where(User.id == user_id).values(**update_data).returning(User)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        updated_user = result.scalar_one()
        logger.info("User updated")
        return self._map_user_response(updated_user, requester)

    async def deactivate_user(self, user_id: UUID, requester: User) -> Response:
        """
        Deactivate a user (soft delete).
        """
        user = await self._get_user_with_access(user_id, requester)

        if requester.role == UserRole.USER:
            if requester.id != user.id:
                raise ForbiddenException(
                    "Users are not allowed to deactivate other accounts"
                )

        else:

            if requester.id == user.id:
                raise ForbiddenException("Admins cannot deactivate their own account")

        if not user.is_active and user.deleted_at is not None:
            raise ConflictException("User is already deactivated")

        user.is_active = False
        user.deleted_at = get_now()
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("User deactivated")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
