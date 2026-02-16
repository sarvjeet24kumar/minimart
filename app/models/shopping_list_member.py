"""
Shopping List Member Model
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import MemberRole
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.shopping_list import ShoppingList
    from app.models.user import User


class ShoppingListMember(BaseModel):
    """
    Shopping list membership entity.
    """

    __tablename__ = "shopping_list_members"
    __table_args__ = (
        UniqueConstraint(
            "shopping_list_id", "user_id", name="uq_members_list_user"
        ),
        Index("idx_members_shopping_list_id", "shopping_list_id"),
        Index("idx_members_user_id", "user_id"),
    )

    shopping_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MemberRole] = mapped_column(
        ENUM(MemberRole, name="member_role", create_type=True),
        default=MemberRole.MEMBER,
        nullable=False,
    )
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_add_item: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_update_item: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_delete_item: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    shopping_list: Mapped["ShoppingList"] = relationship(
        "ShoppingList", back_populates="members"
    )
    user: Mapped["User"] = relationship("User", back_populates="list_memberships")

    def __repr__(self) -> str:
        # Use __dict__ to avoid triggering lazy loads/refresh if detached during error reporting
        d = self.__dict__
        list_id = d.get("shopping_list_id", "???")
        user_id = d.get("user_id", "???")
        role = d.get("role", "???")
        return f"<ShoppingListMember(list_id={list_id}, user_id={user_id}, role={role})>"

    @property
    def username(self) -> str:
        return self.user.username if self.user else "Unknown"
    @property
    def email(self) -> str:
        return self.user.email if self.user else "Unknown"

    @property
    def is_owner(self) -> bool:
        return self.role == MemberRole.OWNER
