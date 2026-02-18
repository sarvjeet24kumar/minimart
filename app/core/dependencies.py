"""
FastAPI Dependencies
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE
from app.common.enums import MemberRole, UserRole
from app.core.security import decode_token
from app.db.session import get_db
from app.exceptions import (
    ForbiddenException,
    NotFoundException,
    TenantInactiveException,
    UnauthorizedException,
)
from app.exceptions.base import MiniMartException
from app.core.logging import get_logger
from app.models.shopping_list import ShoppingList

logger = get_logger(__name__)
from app.models.shopping_list_member import ShoppingListMember
from app.models.tenant import Tenant
from app.models.user import User
from app.services.redis_service import RedisService


security = HTTPBearer(auto_error=True)


class PaginationParams:
    """Dependency for normalized pagination parameters."""

    def __init__(self, page: int = Query(DEFAULT_PAGE, ge=DEFAULT_PAGE), size: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE)):
        self.page = page
        self.size = size
        self.skip = (self.page - 1) * self.size


async def get_tenant_id(
    tenant_id: Annotated[str | None, Header(alias="Tenant-ID")] = None,
) -> UUID | None:
    """
    Dependency to extract Tenant-ID from header.
    """
    if not tenant_id or tenant_id.lower() == "none":
        return None

    try:
        return UUID(tenant_id)
    except ValueError as e:
        raise NotFoundException("Invalid Tenant-ID format") from e


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    """
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as e:
        raise UnauthorizedException(f"Invalid token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type")

    token_id = payload.get("jti")
    if token_id and await RedisService.is_access_token_blacklisted(token_id):
        raise UnauthorizedException("Token has been revoked")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found")

    if not (user.is_active and not user.deleted_at):
        raise ForbiddenException("User account is inactive or deleted")

    if user.tenant_id:
        result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant or not tenant.is_active:
            raise TenantInactiveException()

    return user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current user ensuring email is verified.
    """
    if not current_user.is_email_verified:
        raise MiniMartException(
            status_code=403,
            code="ACCOUNT_NOT_VERIFIED",
            message="Please verify your account before continuing.",
        )
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.
    """

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_verified_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(f"Unauthorized access attempt: Required roles { [r.value for r in allowed_roles] }")
            raise ForbiddenException(
                f"This action requires one of these roles: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker


async def get_shopping_list(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShoppingList:
    """
    Get a shopping list ensuring tenant isolation.
    """
    result = await db.execute(select(ShoppingList).where(ShoppingList.id == list_id))
    shopping_list = result.scalar_one_or_none()

    if not shopping_list:
        raise NotFoundException("Shopping list not found")

    if shopping_list.tenant_id != current_user.tenant_id:
        raise ForbiddenException("Cross-tenant access denied")

    return shopping_list


async def get_list_membership(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShoppingListMember:
    """
    Get current user's membership in a shopping list.
    """
    await get_shopping_list(list_id, current_user, db)

    result = await db.execute(
        select(ShoppingListMember).where(
            ShoppingListMember.shopping_list_id == list_id,
            ShoppingListMember.user_id == current_user.id,
            ShoppingListMember.deleted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise ForbiddenException("You are not an accepted member of this list")

    return membership


async def require_list_owner(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShoppingListMember:
    """
    Require current user to be the owner of a shopping list.

    """
    membership = await get_list_membership(list_id, current_user, db)

    if membership.role != MemberRole.OWNER:
        raise ForbiddenException("Only the list owner can perform this action")

    return membership
