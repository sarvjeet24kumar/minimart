"""
Shopping List Endpoints
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import PaginationParams, get_current_verified_user
from app.core.logging import get_logger
from app.core.rate_limit import RateLimit
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListDetailResponse,
    ShoppingListResponse,
    ShoppingListSummaryResponse,
    ShoppingListUpdate,
)
from app.schemas.shopping_list_member import (
    MemberResponse,
    UpdateMemberPermissions,
)
from app.services.shopping_list import ListMemberService, ShoppingListService

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(RateLimit(settings.RATE_LIMIT_DEFAULT, scope="lists"))])

@router.post(
    "",
    response_model=ShoppingListResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="lists"))],
)
async def create_shopping_list(
    data: ShoppingListCreate,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new shopping list.
    """
    list_service = ShoppingListService(db)
    return await list_service.create_list(current_user, data)


@router.get(
    "",
    response_model=PaginatedResponse[ShoppingListSummaryResponse],
    status_code=status.HTTP_200_OK,
)
async def list_shopping_lists(
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    include_archived: bool = False,
):
    """
    Get all shopping lists visible to the user.
    """
    list_service = ShoppingListService(db)
    return await list_service.get_user_lists(
        current_user,
        pagination=pagination,
        include_archived=include_archived,
    )

@router.get(
    "/{list_id}",
    response_model=ShoppingListDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_shopping_list(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a shopping list with members and items.
    """
    list_service = ShoppingListService(db)
    return await list_service.get_list(list_id, current_user)


@router.patch(
    "/{list_id}",
    response_model=ShoppingListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="lists"))],
)
async def update_shopping_list(
    list_id: UUID,
    data: ShoppingListUpdate,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a shopping list.
    """
    list_service = ShoppingListService(db)
    return await list_service.update_list(list_id, current_user, data)


@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="lists"))],
)
async def delete_shopping_list(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a shopping list.
    """
    list_service = ShoppingListService(db)
    await list_service.delete_list(list_id, current_user)


@router.get(
    "/{list_id}/members",
    response_model=PaginatedResponse[MemberResponse],
    status_code=status.HTTP_200_OK,
)
async def list_members(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    include_deleted: bool = False,
):
    """
    Get all members of a shopping list.
    """
    member_service = ListMemberService(db)
    return await member_service.get_members(
        list_id,
        current_user,
        pagination=pagination,
        include_deleted=include_deleted,
    )

@router.delete(
    "/{list_id}/members/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_member(
    list_id: UUID,
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Remove a member from the shopping list.
    """
    member_service = ListMemberService(db)
    await member_service.remove_member(list_id, user_id, current_user)
    return MessageResponse(message="Member removed successfully")


@router.patch(
    "/{list_id}/members/{user_id}",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
)
async def update_member_permissions(
    list_id: UUID,
    user_id: UUID,
    data: UpdateMemberPermissions,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a member's permission flags.
    """
    member_service = ListMemberService(db)
    return await member_service.update_member_permissions(
        list_id, user_id, current_user, data
    )
