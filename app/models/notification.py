"""
Notification Model
"""

import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import NotificationType
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.shopping_list import ShoppingList
    from app.models.user import User


class Notification(BaseModel):
    """
    Notification entity for user notifications.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_user_unread", "user_id", "is_read"),
        Index("idx_notifications_created_at", "user_id", "created_at"),
        Index("idx_notifications_type", "user_id", "type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    shopping_list_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        ENUM(NotificationType, name="notification_type", create_type=True),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    shopping_list: Mapped[Optional["ShoppingList"]] = relationship(
        "ShoppingList", back_populates="notifications"
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type})>"
