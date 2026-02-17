"""
Shopping List Model
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.constants import MAX_LENGTH_NAME
from app.common.enums import ItemStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.invitation import ShoppingListInvite
    from app.models.item import Item
    from app.models.notification import Notification
    from app.models.shopping_list_member import ShoppingListMember
    from app.models.tenant import Tenant
    from app.models.user import User


class ShoppingList(BaseModel):
    """
    Shopping list entity.
    """

    __tablename__ = "shopping_lists"
    __table_args__ = (
        Index("idx_shopping_lists_tenant_id", "tenant_id"),
        Index("idx_shopping_lists_owner_id", "owner_id"),
        Index("idx_shopping_lists_created_at", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(MAX_LENGTH_NAME), nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="shopping_lists")
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_lists",
        foreign_keys=[owner_id],
    )
    members: Mapped[list["ShoppingListMember"]] = relationship(
        "ShoppingListMember",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    items: Mapped[list["Item"]] = relationship(
        "Item",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(Item.created_at)",
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessage.created_at",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    invites: Mapped[list["ShoppingListInvite"]] = relationship(
        "ShoppingListInvite",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def item_count(self) -> int:
        return len(self.items) if self.items else 0

    @property
    def pending_count(self) -> int:
        if not self.items:
            return 0
        return sum(1 for item in self.items if item.status == ItemStatus.PENDING)

    @property
    def purchased_count(self) -> int:
        if not self.items:
            return 0
        return sum(1 for item in self.items if item.status == ItemStatus.PURCHASED)

    @property
    def member_count(self) -> int:
        if not self.members:
            return 0
        return sum(1 for m in self.members if m.deleted_at is None)

    # This will be manually attached by the service for summary responses
    @property
    def role(self) -> str:
        return getattr(self, "_role", "MEMBER") or "MEMBER"

    @role.setter
    def role(self, value: str):
        self._role = value

    def __repr__(self) -> str:
        return f"<ShoppingList(id={self.id}, name='{self.name}')>"
