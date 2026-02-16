"""
Shopping List Member Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.common.enums import MemberRole
from app.schemas.common import NormalizedModel


class MemberResponse(BaseModel):
    """Member response schema with permission flags."""

    id: UUID
    user_id: UUID
    username: str
    email: str
    role: MemberRole
    can_view: bool = True
    can_add_item: bool = False
    can_update_item: bool = False
    can_delete_item: bool = False
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UpdateMemberPermissions(NormalizedModel):
    """Schema for updating member permissions (Owner/Tenant Admin only)."""

    can_view: bool | None = None
    can_add_item: bool | None = None
    can_update_item: bool | None = None
    can_delete_item: bool | None = None