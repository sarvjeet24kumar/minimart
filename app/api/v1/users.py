"""
User Management Endpoints
"""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.dependencies import (
    PaginationParams,
    get_current_verified_user, 
    require_role,
)
from app.core.config import settings
from app.core.rate_limit import RateLimit
from app.db.session import get_db
from app.exceptions import ForbiddenException
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserAdminResponse, UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(dependencies=[Depends(RateLimit(settings.RATE_LIMIT_DEFAULT, scope="users"))])


@router.post(
    "",
    response_model=UserAdminResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="users"))],
)
async def create_user(
    data: UserCreate,
    current_user: Annotated[
        User, Depends(require_role(UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    """
    Create a new user.
    """
    user_service = UserService(db)

    if current_user.role == UserRole.SUPER_ADMIN:
        user = await user_service.create_user(
            data=data,
            role=UserRole.TENANT_ADMIN,
            background_tasks=background_tasks,
        )
    elif current_user.role == UserRole.TENANT_ADMIN:
        user = await user_service.create_user(
            data=data,
            tenant_id=current_user.tenant_id,
            role=UserRole.USER,
            background_tasks=background_tasks,
        )
    else:
        raise ForbiddenException("Only Admins can create users")

    return user


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def list_users(
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
):
    """
    List users based on role.
    """
    user_service = UserService(db)

    if current_user.role == UserRole.SUPER_ADMIN:
        items, total = await user_service.get_users_in_tenant(
            requester=current_user,
            skip=pagination.skip, 
            limit=pagination.size
        )
    else:
        items, total = await user_service.get_users_in_tenant(
            requester=current_user,
            tenant_id=current_user.tenant_id,
            skip=pagination.skip,
            limit=pagination.size,
        )

    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        return PaginatedResponse(
            data=[UserAdminResponse.model_validate(u) for u in items],
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=ceil(total / pagination.size) if total > 0 else 1,
        )

    return PaginatedResponse(
        data=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total > 0 else 1,
    )


@router.get(
    "/{user_id}",
    response_model=UserAdminResponse | UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific user.
    """
    user_service = UserService(db)
    user = await user_service.get_user(user_id, current_user)

    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        return UserAdminResponse.model_validate(user)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserAdminResponse | UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="users"))],
)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a user.
    """
    user_service = UserService(db)
    user = await user_service.update_user(user_id, current_user, data)

    if current_user.role in [UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN]:
        return UserAdminResponse.model_validate(user)
    return UserResponse.model_validate(user)



@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Deactivate a user (soft delete).
    """
    user_service = UserService(db)
    return await user_service.deactivate_user(user_id, current_user)

