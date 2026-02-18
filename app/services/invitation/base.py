"""
Base Invitation Service
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.exceptions import ForbiddenException
from app.models.user import User


class BaseInvitationService:
    """Base class for all invitation services."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _block_super_admin(self, user: User) -> None:
        """Block Super Admin from all shopping list operations."""
        if user.role == UserRole.SUPER_ADMIN:
            raise ForbiddenException("Super Admin cannot access shopping list operations")
