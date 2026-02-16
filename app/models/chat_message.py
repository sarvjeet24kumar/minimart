"""
Chat Message Model
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.constants import MAX_CHAT_MESSAGE_LENGTH

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.shopping_list import ShoppingList
    from app.models.user import User


class ChatMessage(BaseModel):
    """
    Chat message entity for real-time chat within shopping lists.

    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_shopping_list_id", "shopping_list_id"),
        Index("idx_chat_sender_id", "sender_id"),
        Index("idx_chat_created_at", "shopping_list_id", "created_at"),
        CheckConstraint(f"length(content) <= {MAX_CHAT_MESSAGE_LENGTH}", name="check_chat_message_length"),
    )

    shopping_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(String(MAX_CHAT_MESSAGE_LENGTH), nullable=False)

    shopping_list: Mapped["ShoppingList"] = relationship(
        "ShoppingList", back_populates="chat_messages"
    )
    sender: Mapped["User"] = relationship("User", back_populates="sent_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, list_id={self.shopping_list_id}, sender_id={self.sender_id})>"
