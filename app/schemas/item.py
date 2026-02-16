"""
Item Schemas

"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import ItemStatus
from app.schemas.common import NormalizedModel


from app.common.constants import (
    MAX_LENGTH_NAME,
    MIN_LENGTH_NAME,
    MIN_ITEM_QUANTITY,
    MAX_ITEM_QUANTITY,
    DEFAULT_ITEM_QUANTITY,
)


class ItemCreate(NormalizedModel):
    """Item creation schema."""

    name: str = Field(..., min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)
    quantity: int = Field(
        default=DEFAULT_ITEM_QUANTITY, ge=MIN_ITEM_QUANTITY, le=MAX_ITEM_QUANTITY
    )


class ItemUpdate(NormalizedModel):
    """Item update schema."""

    name: str | None = Field(
        None, min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME
    )
    quantity: int | None = Field(None, ge=MIN_ITEM_QUANTITY, le=MAX_ITEM_QUANTITY)
    status: ItemStatus | None = None


class ItemResponse(NormalizedModel):
    """Item response schema."""

    id: UUID
    name: str
    quantity: int
    shopping_list_id: UUID
    status: ItemStatus
    added_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ItemStatusUpdate(BaseModel):
    """Quick status update schema."""

    status: ItemStatus
