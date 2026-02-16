"""
Shopping List Schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import ItemStatus, MemberRole
from app.schemas.common import NormalizedModel


from app.common.constants import MAX_LENGTH_NAME, MIN_LENGTH_NAME

class ShoppingListCreate(NormalizedModel):
    """Shopping list creation schema."""

    name: str = Field(..., min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)


class ShoppingListUpdate(NormalizedModel):
    """Shopping list update schema."""

    name: str | None = Field(None, min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)


class MemberBrief(BaseModel):
    """Brief member info for list response."""

    user_id: UUID
    username: str
    role: MemberRole
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShoppingListResponse(NormalizedModel):
    """Shopping list response schema."""

    id: UUID
    name: str
    tenant_id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemBrief(BaseModel):
    """Brief item info for list response."""

    id: UUID
    name: str
    quantity: int
    status: ItemStatus
    added_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShoppingListDetailResponse(ShoppingListResponse):
    """Detailed shopping list response with members and items."""

    members: list[MemberBrief] = []
    items: list[ItemBrief] = []
    item_count: int = 0
    pending_count: int = 0
    purchased_count: int = 0


class ShoppingListSummaryResponse(BaseModel):
    """Summary response for list of shopping lists."""

    id: UUID
    name: str
    role: str  # User's role in this list
    item_count: int
    member_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
