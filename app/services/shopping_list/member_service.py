"""
Shopping List Member Management Service
"""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.core.logging import get_logger
from app.core.time import get_now
from app.exceptions import ForbiddenException, NotFoundException
from app.models.shopping_list_member import ShoppingListMember
from app.websocket.manager import manager
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.shopping_list_member import MemberResponse
from app.services.shopping_list.base import BaseListService

logger = get_logger(__name__)


class ListMemberService(BaseListService):
    """Handles membership and permission operations."""

    async def get_members(
        self,
        list_id: UUID,
        user: User,
        pagination: PaginationParams,
        include_deleted: bool = False,
    ) -> PaginatedResponse[MemberResponse]:
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
            .offset(pagination.skip)
            .limit(pagination.size)
        )
        members = result.scalars().all()

        return PaginatedResponse(
            data=[MemberResponse.model_validate(m) for m in members],
            total=total,
            page=pagination.page,
            size=pagination.size
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

        membership.deleted_at = get_now()
        await self.db.commit()

        # Kick user from chat immediately
        await manager.kick_user_from_list(str(member_user_id), str(list_id))

        logger.info("Member removed from list")

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

        await self.db.refresh(membership, ["user"])

        logger.info("Member permissions updated")

        return membership
