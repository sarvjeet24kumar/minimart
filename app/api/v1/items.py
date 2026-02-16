"""
Item Endpoints
"""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ItemStatus
from app.core.dependencies import PaginationParams, get_current_verified_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.item import ItemCreate, ItemResponse, ItemStatusUpdate, ItemUpdate
from app.services.shopping_list import ListItemService

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/{list_id}/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    list_id: UUID,
    data: ItemCreate,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add an item to a shopping list.
    """
    item_service = ListItemService(db)
    return await item_service.add_item(list_id, current_user, data)


@router.get(
    "/{list_id}/items",
    response_model=PaginatedResponse[ItemResponse],
    status_code=status.HTTP_200_OK,
)
async def get_items(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    status: ItemStatus | None = None,
):
    """
    Get all items in a shopping list.
    """
    item_service = ListItemService(db)
    items, total = await item_service.get_items(
        list_id, current_user, skip=pagination.skip, limit=pagination.size, status=status
    )

    return PaginatedResponse(
        data=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total > 0 else 1,
    )


@router.get(
    "/{list_id}/items/{item_id}",
    response_model=ItemResponse,
    status_code=status.HTTP_200_OK,
)
async def get_item(
    list_id: UUID,
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific item from a shopping list.
    """
    item_service = ListItemService(db)
    return await item_service.get_item(list_id, item_id, current_user)


@router.patch(
    "/{list_id}/items/{item_id}",
    response_model=ItemResponse,
    status_code=status.HTTP_200_OK,
)
async def update_item(
    list_id: UUID,
    item_id: UUID,
    data: ItemUpdate,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an item in a shopping list.
    """
    item_service = ListItemService(db)
    return await item_service.update_item_scoped(list_id, item_id, current_user, data)


@router.patch(
    "/{list_id}/items/{item_id}/status",
    response_model=ItemResponse,
    status_code=status.HTTP_200_OK,
)
async def update_item_status(
    list_id: UUID,
    item_id: UUID,
    data: ItemStatusUpdate,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Quick update for item status (mark as purchased/pending).
    """
    item_service = ListItemService(db)
    from app.schemas.item import ItemUpdate
    return await item_service.update_item_scoped(
        list_id, item_id, current_user, ItemUpdate(status=data.status)
    )


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    list_id: UUID,
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete an item from a shopping list.
    """
    item_service = ListItemService(db)
    await item_service.delete_item_scoped(list_id, item_id, current_user)
