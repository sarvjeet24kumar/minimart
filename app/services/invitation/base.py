"""
Base Invitation Service
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import ShoppingListInvite
from app.common.enums import UserRole
from app.exceptions import ForbiddenException
from app.models.user import User
from app.websocket.manager import manager


class BaseInvitationService:
    """Base class for all invitation services."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _block_super_admin(self, user: User) -> None:
        """Block Super Admin from all shopping list operations."""
        if user.role == UserRole.SUPER_ADMIN:
            raise ForbiddenException("Super Admin cannot access shopping list operations")

    async def _broadcast(
        self, list_id: UUID, event_type: str, data: dict, exclude_user_id: UUID | None = None, only_scoped: bool = False
    ) -> None:
        """Broadcast event directly to connected subscribers."""
        await manager.broadcast_event(
            str(list_id), 
            event_type, 
            data, 
            exclude_user_id=str(exclude_user_id) if exclude_user_id else None,
            only_scoped=only_scoped
        )
