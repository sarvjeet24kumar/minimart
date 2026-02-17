"""
Shopping List Invitation Model
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.constants import MAX_LENGTH_TOKEN
from app.common.enums import InviteStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.shopping_list import ShoppingList
    from app.models.user import User


class ShoppingListInvite(BaseModel):
    """
    Shopping list invitation entity.

    """

    __tablename__ = "shopping_list_invites"
    __table_args__ = (
        # Composite indexes or specialized constraints go here
    )

    shopping_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(MAX_LENGTH_TOKEN), unique=True, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        ENUM(InviteStatus, name="invite_status", create_type=True),
        default=InviteStatus.PENDING,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    shopping_list: Mapped["ShoppingList"] = relationship(
        "ShoppingList", back_populates="invites"
    )
    invited_user: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[invited_user_id],
        back_populates="received_invitations"
    )
    invited_by_user: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[invited_by_user_id],
        back_populates="sent_invitations"
    )

    @property
    def list_name(self) -> str | None:
        return self.shopping_list.name if self.shopping_list else None

    @property
    def invited_email(self) -> str | None:
        return self.invited_user.email if self.invited_user else None

    @property
    def invited_username(self) -> str | None:
        return self.invited_user.username if self.invited_user else None

    @property
    def invited_by_username(self) -> str | None:
        return self.invited_by_user.username if self.invited_by_user else None

    def __repr__(self) -> str:
        return f"<ShoppingListInvite(id={self.id}, list_id={self.shopping_list_id}, status={self.status})>"
