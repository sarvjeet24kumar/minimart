"""
Item Endpoints
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ItemStatus
from app.core.config import settings
from app.core.dependencies import PaginationParams, get_current_verified_user
from app.core.rate_limit import RateLimit
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.services.shopping_list import ListItemService


logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(RateLimit(settings.RATE_LIMIT_DEFAULT, scope="items"))])


@router.post(
    "/{list_id}/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="items"))],
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
    return await item_service.get_items(
        list_id, current_user, pagination, status=status
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
    dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="items"))],
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
