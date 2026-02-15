"""
Item Schemas

"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import ItemStatus
from app.schemas.common import NormalizedModel


class ItemCreate(NormalizedModel):
    """Item creation schema."""

    name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1)


class ItemUpdate(NormalizedModel):
    """Item update schema."""

    name: str | None = Field(None, min_length=1, max_length=255)
    quantity: int | None = Field(None, ge=1)
    status: ItemStatus | None = None


class ItemResponse(NormalizedModel):
    """Item response schema."""

    id: UUID
    name: str
    quantity: int
    shopping_list_id: UUID
    added_by: UUID | None
    added_by_username: str | None = None
    updated_by: UUID | None = None
    status: ItemStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemStatusUpdate(BaseModel):
    """Quick status update schema."""

    status: ItemStatus
