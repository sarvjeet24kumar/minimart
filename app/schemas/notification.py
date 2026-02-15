"""
Notification Schemas
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import NotificationType
from app.schemas.common import NormalizedModel


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: UUID
    user_id: UUID
    shopping_list_id: UUID | None = None
    type: NotificationType
    payload: dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(NormalizedModel):
    """Notification update schema (mostly for marking as read)."""

    is_read: bool


class NotificationFilter(NormalizedModel):
    """Query parameters for filtering notifications."""

    is_read: bool | None = None
