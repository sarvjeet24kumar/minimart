"""
Base Shopping List Service

Contains shared logic for access control, permissions, and internal event publishing.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.common.enums import MemberRole, UserRole
from app.exceptions import ForbiddenException, NotFoundException
from app.models.shopping_list import ShoppingList
from app.models.shopping_list_member import ShoppingListMember
from app.models.user import User
from app.websocket.manager import manager


logger = get_logger(__name__)


class BaseListService:
    """Foundational class for shopping list-related services."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _block_super_admin(self, user: User) -> None:
        """Block Super Admin from all shopping list operations."""
        if user.role == UserRole.SUPER_ADMIN:
            logger.warning("Super Admin attempted shopping list operation")
            raise ForbiddenException(
                "Super Admin cannot access shopping list operations"
            )

    async def _get_list_with_access(
        self,
        list_id: UUID,
        user: User,
        require_owner_or_admin: bool = False,
    ) -> tuple[ShoppingList, ShoppingListMember | None]:
        """
        Central access gate for shopping list operations.
        """
        self._block_super_admin(user)

        result = await self.db.execute(
            select(ShoppingList)
            .options(
                selectinload(ShoppingList.members).selectinload(
                    ShoppingListMember.user
                ),
                selectinload(ShoppingList.items),
            )
            .where(ShoppingList.id == list_id)
        )
        shopping_list = result.scalar_one_or_none()

        if not shopping_list:
            logger.warning("Shopping list not found")
            raise NotFoundException("Shopping list not found")



        if shopping_list.tenant_id != user.tenant_id:
            logger.warning("Cross-tenant access denied to shopping list")
            raise ForbiddenException("Cross-tenant access denied")

        if user.role == UserRole.TENANT_ADMIN:
            membership = next(
                (m for m in shopping_list.members if m.user_id == user.id and m.deleted_at is None), None
            )
            return shopping_list, membership

        membership = next(
            (m for m in shopping_list.members if m.user_id == user.id and m.deleted_at is None), None
        )
        if not membership:
            logger.warning("Unauthorized access attempt: Not a member of this list")
            raise ForbiddenException("You are not a member of this list")

        if require_owner_or_admin and membership.role != MemberRole.OWNER:
            logger.warning(
                "Unauthorized action attempt: Owner or Tenant Admin required"
            )
            raise ForbiddenException("Only the owner can perform this action")

        return shopping_list, membership

    def _check_item_permission(
        self, user: User, membership: ShoppingListMember | None, permission: str
    ) -> None:
        """
        Check if user has a specific item permission.
        """
        if user.role == UserRole.TENANT_ADMIN:
            return

        if not membership:
            logger.warning("Item permission check failed: Not a member")
            raise ForbiddenException("You are not a member of this list")

        if membership.role == MemberRole.OWNER:
            return

        if not getattr(membership, permission, False):
            logger.warning(f"Item permission check failed: Missing {permission}")
            raise ForbiddenException("You don't have permission to perform this action")

    def _check_not_deleted(self, shopping_list: ShoppingList) -> None:
        """Raise ForbiddenException if the list is soft-deleted."""
        if shopping_list.deleted_at:
            logger.warning(f"Mutation blocked: List {shopping_list.id} is soft-deleted")
            raise ForbiddenException("This list is deleted.")

    async def _publish_event(
        self,
        list_id: UUID,
        event_type: str,
        data: dict,
        exclude_user_id: UUID | None = None,
        only_scoped: bool = False,
    ) -> None:
        """Broadcast event directly to connected subscribers."""
        await manager.broadcast_event(
            str(list_id),
            event_type,
            data,
            exclude_user_id=str(exclude_user_id) if exclude_user_id else None,
            only_scoped=only_scoped,
        )
