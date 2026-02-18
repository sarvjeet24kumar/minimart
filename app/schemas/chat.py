"""
Chat Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.constants import MAX_CHAT_MESSAGE_LENGTH, MIN_LENGTH_CHAT_MESSAGE
from app.schemas.common import NormalizedModel


class ChatMessageRequest(NormalizedModel):
    """Schema for sending a chat message."""

    message: str = Field(
        ..., min_length=MIN_LENGTH_CHAT_MESSAGE, max_length=MAX_CHAT_MESSAGE_LENGTH,
        description="Chat message content",
    )


class ChatMessageResponse(BaseModel):
    """Schema for a single chat message."""

    id: UUID
    shopping_list_id: UUID
    sender_id: UUID
    sender_name: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


