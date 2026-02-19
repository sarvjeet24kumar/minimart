"""
Shopping List Management Service
"""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.common.enums import MemberRole, NotificationType, UserRole
from app.core.logging import get_logger
from app.core.time import get_now
from app.exceptions import ForbiddenException
from app.models.shopping_list import ShoppingList
from app.models.shopping_list_member import ShoppingListMember
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListResponse,
    ShoppingListSummaryResponse,
    ShoppingListUpdate,
)
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

        logger.info("Shopping list created")
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
        self,
        user: User,
        pagination: PaginationParams,
        include_archived: bool = False,
    ) -> PaginatedResponse[ShoppingListSummaryResponse]:
        """Get shopping lists visible to the user."""
        self._block_super_admin(user)

        if user.role == UserRole.TENANT_ADMIN:
            filter_cond = [ShoppingList.tenant_id == user.tenant_id]
            if not include_archived:
                filter_cond.append(ShoppingList.deleted_at.is_(None))

            count_result = await self.db.execute(
                select(func.count())
                .select_from(ShoppingList)
                .where(and_(*filter_cond))
            )
            total = count_result.scalar_one()

            result = await self.db.execute(
                select(ShoppingList)
                .options(
                    selectinload(ShoppingList.items),
                    selectinload(ShoppingList.members),
                )
                .where(and_(*filter_cond))
                .order_by(ShoppingList.created_at.desc())
                .offset(pagination.skip)
                .limit(pagination.size)
            )
            shopping_lists = result.scalars().all()

            items = []
            for shopping_list in shopping_lists:
                admin_membership = next(
                    (m for m in shopping_list.members if m.user_id == user.id and m.deleted_at is None), None
                )
                role = (
                    admin_membership.role.value
                    if admin_membership
                    else UserRole.TENANT_ADMIN.value
                )
                
                items.append(
                    ShoppingListSummaryResponse(
                        id=shopping_list.id,
                        name=shopping_list.name,
                        role=role,
                        item_count=len([i for i in shopping_list.items if i.deleted_at is None]),
                        member_count=len([m for m in shopping_list.members if m.deleted_at is None]),
                        created_at=shopping_list.created_at,
                        deleted_at=shopping_list.deleted_at,
                    )
                )

            return PaginatedResponse(
                data=items,
                total=total,
                page=pagination.page,
                size=pagination.size
            )
        else:

            filter_cond = [
                ShoppingListMember.user_id == user.id,
                ShoppingListMember.deleted_at.is_(None),
                ShoppingList.deleted_at.is_(None),
            ]

            count_result = await self.db.execute(
                select(func.count())
                .select_from(ShoppingListMember)
                .join(ShoppingList, ShoppingList.id == ShoppingListMember.shopping_list_id)
                .where(and_(*filter_cond))
            )
            total = count_result.scalar_one()

            result = await self.db.execute(
                select(ShoppingListMember)
                .join(ShoppingList, ShoppingList.id == ShoppingListMember.shopping_list_id)
                .options(
                    selectinload(ShoppingListMember.shopping_list).selectinload(
                        ShoppingList.items
                    ),
                    selectinload(ShoppingListMember.shopping_list).selectinload(
                        ShoppingList.members
                    ),
                )
                .where(and_(*filter_cond))
                .order_by(ShoppingListMember.joined_at.desc())
                .offset(pagination.skip)
                .limit(pagination.size)
            )
            memberships = result.scalars().all()

            items = []
            for membership in memberships:
                shopping_list = membership.shopping_list
                
                items.append(
                    ShoppingListSummaryResponse(
                        id=shopping_list.id,
                        name=shopping_list.name,
                        role=membership.role.value,
                        item_count=len([i for i in shopping_list.items if i.deleted_at is None]),
                        member_count=len([m for m in shopping_list.members if m.deleted_at is None]),
                        created_at=shopping_list.created_at,
                        deleted_at=shopping_list.deleted_at,
                    )
                )

            return PaginatedResponse(
                data=items,
                total=total,
                page=pagination.page,
                size=pagination.size
            )

    async def update_list(
        self, list_id: UUID, user: User, data: ShoppingListUpdate
    ) -> ShoppingList:
        """
        Update a shopping list.
        """
        shopping_list, _ = await self._get_list_with_access(
            list_id, user, require_owner_or_admin=True
        )


        is_restoring = False
        if "deleted_at" in data.model_fields_set:
            if user.role != UserRole.TENANT_ADMIN:
                raise ForbiddenException(
                    "Only Tenant Admins can modify the deleted_at field"
                )
            if data.deleted_at is None and shopping_list.deleted_at:
                is_restoring = True

        if not is_restoring:
            self._check_not_deleted(shopping_list)

        if data.name is not None:
            shopping_list.name = data.name

        if "deleted_at" in data.model_fields_set:
            shopping_list.deleted_at = data.deleted_at

        await self.db.commit()
        await self.db.refresh(shopping_list)

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
        self._check_not_deleted(shopping_list)
        shopping_list.deleted_at = get_now()
        await self.db.commit()

        logger.info("Shopping list deleted")

        return True
