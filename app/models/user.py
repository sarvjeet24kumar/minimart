"""
User Model
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.constants import (
    MAX_LENGTH_EMAIL,
    MAX_LENGTH_NAME,
    MAX_LENGTH_PASSWORD_HASH,
    MAX_LENGTH_USERNAME,
)
from app.common.enums import UserRole
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.invitation import ShoppingListInvite
    from app.models.item import Item
    from app.models.notification import Notification
    from app.models.shopping_list import ShoppingList
    from app.models.shopping_list_member import ShoppingListMember
    from app.models.tenant import Tenant


class User(BaseModel):
    """
    User entity with tenant association.
    """

    __tablename__ = "users"
    __table_args__ = (
        # Standard tenant-scoped uniqueness
        UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email")
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
    )
    first_name: Mapped[str] = mapped_column(String(MAX_LENGTH_NAME), nullable=False)
    last_name: Mapped[str] = mapped_column(String(MAX_LENGTH_NAME), nullable=False)
    username: Mapped[str] = mapped_column(
        String(MAX_LENGTH_USERNAME), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(MAX_LENGTH_EMAIL), nullable=False, index=True
    )
    password: Mapped[str] = mapped_column(String(MAX_LENGTH_PASSWORD_HASH), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name="user_role", create_type=True),
        default=UserRole.USER,
        nullable=False,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    owned_lists: Mapped[list["ShoppingList"]] = relationship(
        "ShoppingList",
        back_populates="owner",
        foreign_keys="ShoppingList.owner_id",
        lazy="selectin",
    )
    list_memberships: Mapped[list["ShoppingListMember"]] = relationship(
        "ShoppingListMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    added_items: Mapped[list["Item"]] = relationship(
        "Item",
        back_populates="added_by_user",
        foreign_keys="Item.added_by",
        lazy="selectin",
    )
    sent_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="sender",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sent_invitations: Mapped[list["ShoppingListInvite"]] = relationship(
        "ShoppingListInvite",
        back_populates="invited_by_user",
        foreign_keys="[ShoppingListInvite.invited_by_user_id]",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    received_invitations: Mapped[list["ShoppingListInvite"]] = relationship(
        "ShoppingListInvite",
        back_populates="invited_user",
        foreign_keys="[ShoppingListInvite.invited_user_id]",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role={self.role})>"