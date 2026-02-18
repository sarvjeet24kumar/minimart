"""
Base Service

Shared foundation for all services that need DB access and role guards.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.logging import get_logger
from app.exceptions import ForbiddenException
from app.models.user import User


logger = get_logger(__name__)


class BaseService:
    """Common base for all services."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _block_super_admin(self, user: User) -> None:
        """Block Super Admin from all shopping list operations."""
        if user.role == UserRole.SUPER_ADMIN:
            logger.warning("Super Admin attempted shopping list operation")
            raise ForbiddenException(
                "Super Admin cannot access shopping list operations"
            )
