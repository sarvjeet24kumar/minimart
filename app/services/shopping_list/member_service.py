"""
Shopping List Member Management Service
"""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.common.constants import (
    DEFAULT_PAGE_SIZE,
    WS_EVENT_MEMBER_LEFT,
    WS_EVENT_MEMBER_REMOVED,
    WS_EVENT_PERMISSIONS_UPDATED,
)
from app.common.enums import NotificationType
from app.core.logging import get_logger
from app.exceptions import ForbiddenException, NotFoundException
from app.models.shopping_list_member import ShoppingListMember
from app.models.user import User
from app.services.notification_service import NotificationService
from app.services.shopping_list.base import BaseListService

logger = get_logger(__name__)

class ListMemberService(BaseListService):
    """Handles membership and permission operations."""

    async def get_members(
        self,
        list_id: UUID,
        user: User,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
        include_deleted: bool = False,
    ) -> tuple[list[ShoppingListMember], int]:
        """Get all members of a shopping list."""
        await self._get_list_with_access(list_id, user)

        filter_cond = [ShoppingListMember.shopping_list_id == list_id]
        if not include_deleted:
            filter_cond.append(ShoppingListMember.deleted_at.is_(None))

        count_result = await self.db.execute(
            select(func.count()).where(and_(*filter_cond))
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(ShoppingListMember)
            .options(selectinload(ShoppingListMember.user))
            .where(and_(*filter_cond))
            .offset(skip)
            .limit(limit)
        )
        members = result.scalars().all()

        return list(members), total

    async def notify_member_removed(self, list_id: UUID, member_user_id: UUID, user: User, shopping_list_name: str):
        """Helper to create notification when a member is removed."""
        notification_service = NotificationService(self.db)
        await notification_service.create_notification(
            user_id=member_user_id,
            notification_type=NotificationType.MEMBER_REMOVED,
            payload={
                "list_name": shopping_list_name,
                "remover_username": user.username,
            },
            shopping_list_id=list_id,
        )

    async def remove_member(
        self, list_id: UUID, member_user_id: UUID, user: User
    ) -> bool:
        """Remove a member from a shopping list."""
        shopping_list, _ = await self._get_list_with_access(
            list_id, user, require_owner_or_admin=True
        )
        self._check_not_deleted(shopping_list)

        if member_user_id == shopping_list.owner_id:
            raise ForbiddenException("Cannot remove the owner from the list")

        result = await self.db.execute(
            select(ShoppingListMember).where(
                and_(
                    ShoppingListMember.shopping_list_id == list_id,
                    ShoppingListMember.user_id == member_user_id,
                )
            )
        )
        membership = result.scalar_one_or_none()

        if not membership or membership.deleted_at:
            raise NotFoundException("Member not found")

        membership.deleted_at = func.now()
        await self.db.commit()

        logger.info("Member removed from list")

        await self._publish_event(
            list_id,
            WS_EVENT_MEMBER_REMOVED,
            {"user_id": str(member_user_id)},
        )

        await self.notify_member_removed(list_id, member_user_id, user, shopping_list.name)

        return True


    async def update_member_permissions(
        self,
        list_id: UUID,
        member_user_id: UUID,
        user: User,
        data,
    ) -> ShoppingListMember:
        """Update a member's permission flags."""
        shopping_list, _ = await self._get_list_with_access(
            list_id, user, require_owner_or_admin=True
        )
        self._check_not_deleted(shopping_list)

        if member_user_id == shopping_list.owner_id:
            raise ForbiddenException("Cannot modify the owner's permissions")

        result = await self.db.execute(
            select(ShoppingListMember)
            .options(selectinload(ShoppingListMember.user))
            .where(
                and_(
                    ShoppingListMember.shopping_list_id == list_id,
                    ShoppingListMember.user_id == member_user_id,
                )
            )
        )
        membership = result.scalar_one_or_none()

        if not membership:
            raise NotFoundException("Member not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(membership, field, value)

        await self.db.commit()

        # Re-fetch with selectinload to avoid DetachedInstanceError/MissingGreenlet during serialization
        result = await self.db.execute(
            select(ShoppingListMember)
            .options(selectinload(ShoppingListMember.user))
            .where(
                and_(
                    ShoppingListMember.shopping_list_id == list_id,
                    ShoppingListMember.user_id == member_user_id,
                )
            )
        )
        membership = result.scalar_one()

        logger.info("Member permissions updated")

        await self._publish_event(
            list_id,
            WS_EVENT_PERMISSIONS_UPDATED,
            {
                "user_id": str(member_user_id),
                "can_add_item": membership.can_add_item,
                "can_update_item": membership.can_update_item,
                "can_delete_item": membership.can_delete_item,
            },
        )

        return membership
