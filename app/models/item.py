"""
Item Model
"""

import uuid
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.shopping_list import ShoppingList
    from app.models.user import User

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.constants import MAX_LENGTH_NAME, MIN_ITEM_QUANTITY, MAX_ITEM_QUANTITY, DEFAULT_ITEM_QUANTITY
from app.common.enums import ItemStatus
from app.models.base import BaseModel


class Item(BaseModel):
    """
    Shopping list item entity.
    """

    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint(f"quantity >= {MIN_ITEM_QUANTITY}", name="check_quantity_positive"),
        Index("idx_items_shopping_list", "shopping_list_id"),
        Index("idx_items_added_by", "added_by"),
    )

    shopping_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(MAX_LENGTH_NAME), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=DEFAULT_ITEM_QUANTITY, nullable=False)
    status: Mapped[ItemStatus] = mapped_column(
        ENUM(ItemStatus, name="item_status", create_type=True),
        default=ItemStatus.PENDING,
        nullable=False,
    )

    # Relationships
    shopping_list: Mapped["ShoppingList"] = relationship(
        "ShoppingList", back_populates="items"
    )
    added_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="added_items",
        foreign_keys=[added_by],
    )
    updated_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
    )
    deleted_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[deleted_by],
    )

    @property
    def is_purchased(self) -> bool:
        return self.status == ItemStatus.PURCHASED
    def __repr__(self) -> str:
        return f"<Item(id={self.id}, name='{self.name}', status={self.status})>"

