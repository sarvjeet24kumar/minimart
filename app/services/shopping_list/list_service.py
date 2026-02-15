"""
Shopping List Management Service
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.common.constants import (
    DEFAULT_PAGE_SIZE,
    WS_EVENT_LIST_DELETED,
    WS_EVENT_LIST_UPDATED,
)
from app.common.enums import ItemStatus, MemberRole, NotificationType, UserRole
from app.core.logging import get_logger
from app.models.shopping_list import ShoppingList
from app.models.shopping_list_member import ShoppingListMember
from app.models.user import User
from app.schemas.shopping_list import ShoppingListCreate, ShoppingListUpdate
from app.services.notification_service import NotificationService
from app.services.shopping_list.base import BaseListService

logger = get_logger(__name__)


class ShoppingListService(BaseListService):
    """Handles core shopping list operations (CRUD)."""

    async def create_list(self, user: User, data: ShoppingListCreate) -> ShoppingList:
        """Create a new shopping list."""
        self._block_super_admin(user)

        shopping_list = ShoppingList(
            tenant_id=user.tenant_id,
            owner_id=user.id,
            name=data.name,
        )
        self.db.add(shopping_list)
        await self.db.flush()

        # Create owner membership with full permissions
        membership = ShoppingListMember(
            shopping_list_id=shopping_list.id,
            user_id=user.id,
            role=MemberRole.OWNER,
            can_view=True,
            can_add_item=True,
            can_update_item=True,
            can_delete_item=True,
        )
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(shopping_list)

        logger.info("Shopping list created: list_id=%s", shopping_list.id)
        return shopping_list

    async def get_list(self, list_id: UUID, user: User) -> ShoppingList:
        """Get a shopping list with detailed information."""
        shopping_list, membership = await self._get_list_with_access(list_id, user)

        role = "MEMBER"
        if user.role == UserRole.TENANT_ADMIN:
            role = "TENANT_ADMIN"
        if membership:
            role = membership.role.value

        shopping_list.role = role
        return shopping_list

    async def get_user_lists(
        self, user: User, skip: int = 0, limit: int = DEFAULT_PAGE_SIZE
    ) -> tuple[list[ShoppingList], int]:
        """Get shopping lists visible to the user."""
        self._block_super_admin(user)

        if user.role == UserRole.TENANT_ADMIN:
            count_result = await self.db.execute(
                select(func.count())
                .select_from(ShoppingList)
                .where(ShoppingList.tenant_id == user.tenant_id)
            )
            total = count_result.scalar_one()

            result = await self.db.execute(
                select(ShoppingList)
                .options(
                    selectinload(ShoppingList.items),
                    selectinload(ShoppingList.members),
                )
                .where(ShoppingList.tenant_id == user.tenant_id)
                .offset(skip)
                .limit(limit)
            )
            shopping_lists = result.scalars().all()

            for shopping_list in shopping_lists:
                admin_membership = next(
                    (m for m in shopping_list.members if m.user_id == user.id), None
                )
                shopping_list.role = (
                    admin_membership.role.value
                    if admin_membership
                    else UserRole.TENANT_ADMIN.value
                )

            return list(shopping_lists), total
        else:
            count_result = await self.db.execute(
                select(func.count()).where(ShoppingListMember.user_id == user.id)
            )
            total = count_result.scalar_one()

            result = await self.db.execute(
                select(ShoppingListMember)
                .options(
                    selectinload(ShoppingListMember.shopping_list).selectinload(
                        ShoppingList.items
                    ),
                    selectinload(ShoppingListMember.shopping_list).selectinload(
                        ShoppingList.members
                    ),
                )
                .where(ShoppingListMember.user_id == user.id)
                .offset(skip)
                .limit(limit)
            )
            memberships = result.scalars().all()

            lists = []
            for membership in memberships:
                shopping_list = membership.shopping_list
                shopping_list.role = membership.role.value
                lists.append(shopping_list)

            return lists, total

    async def update_list(
        self, list_id: UUID, user: User, data: ShoppingListUpdate
    ) -> ShoppingList:
        """Update a shopping list."""
        shopping_list, _ = await self._get_list_with_access(
            list_id, user, require_owner_or_admin=True
        )

        if data.name is not None:
            shopping_list.name = data.name

        await self.db.commit()
        await self.db.refresh(shopping_list)

        logger.info("Shopping list updated: list_id=%s", list_id)

        await self._publish_event(
            list_id,
            WS_EVENT_LIST_UPDATED,
            {"id": str(shopping_list.id), "name": shopping_list.name},
            exclude_user_id=user.id,
        )

        notification_service = NotificationService(self.db)
        await notification_service.notify_list_members(
            list_id=list_id,
            notification_type=NotificationType.LIST_UPDATED,
            payload={"name": shopping_list.name, "updated_by": user.username},
            exclude_user_id=user.id,
        )

        return shopping_list

    async def delete_list(self, list_id: UUID, user: User) -> bool:
        """Delete a shopping list."""
        shopping_list, _ = await self._get_list_with_access(
            list_id, user, require_owner_or_admin=True
        )
        shopping_list.deleted_at = func.now()
        await self.db.commit()

        logger.info("Shopping list deleted: list_id=%s", list_id)

        await self._publish_event(
            list_id,
            WS_EVENT_LIST_DELETED,
            {"id": str(list_id)},
            exclude_user_id=user.id,
        )

        return True
