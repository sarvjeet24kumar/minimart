"""
Invitation Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.constants import MAX_LENGTH_TOKEN, MIN_LENGTH_TOKEN, MSG_INVITE_SENT
from app.common.enums import InviteStatus
from app.schemas.common import NormalizedModel


class InviteRequest(NormalizedModel):
    """Invitation request schema."""

    user_id: UUID


class InviteResponse(BaseModel):
    """Invitation response schema."""

    message: str = MSG_INVITE_SENT
    expires_at: datetime


class InvitationAcceptRequest(NormalizedModel):
    """Accept invitation request."""
    token: str = Field(..., min_length=MIN_LENGTH_TOKEN, max_length=MAX_LENGTH_TOKEN)


class InvitationRejectRequest(NormalizedModel):
    """Reject invitation request."""
    token: str = Field(..., min_length=MIN_LENGTH_TOKEN, max_length=MAX_LENGTH_TOKEN)


class InvitationResponse(BaseModel):
    """Full invitation response."""
    id: UUID
    shopping_list_id: UUID
    list_name: str | None = None
    invited_user_id: UUID
    invited_email: str | None = None
    invited_username: str | None = None
    invited_by_user_id: UUID
    invited_by_username: str | None = None
    status: InviteStatus
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    resent_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
