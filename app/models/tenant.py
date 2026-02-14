"""
Tenant Model

Represents a tenant/organization in the multi-tenant system.
All users, shopping lists, and items belong to a tenant.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.constants import MAX_LENGTH_NAME, MAX_LENGTH_SLUG
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.shopping_list import ShoppingList
    from app.models.user import User


class Tenant(BaseModel):
    """
    Tenant entity for multi-tenancy.
    
    Attributes:
        id: Unique identifier (UUID)
        name: Tenant display name
        is_active: Whether the tenant is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp
    """

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(MAX_LENGTH_NAME), nullable=False)
    slug: Mapped[str] = mapped_column(String(MAX_LENGTH_SLUG), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    shopping_lists: Mapped[list["ShoppingList"]] = relationship(
        "ShoppingList",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}')>"
