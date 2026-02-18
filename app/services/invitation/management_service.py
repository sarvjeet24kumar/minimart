"""
Invitation Management Service
"""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.common.enums import InviteStatus, NotificationType, UserRole
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_invitation_token
from app.core.time import get_now
from app.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.exceptions.base import MiniMartException
from app.models.invitation import ShoppingListInvite
from app.models.shopping_list import ShoppingList
from app.models.shopping_list_member import ShoppingListMember
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.invitation import InviteResponse, InvitationResponse
from app.services.base import BaseService
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService

logger = get_logger(__name__)

class InvitationManagementService(BaseService):
    """Handles creation and administrative management of invitations."""

    async def send_invitation(
        self,
        list_id: UUID,
        user_id: UUID,
        inviter: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> InviteResponse:
        """Create a DB-backed invitation to join a shopping list."""
        if inviter.role == UserRole.SUPER_ADMIN:
            logger.warning("Super Admin attempted shopping list operation")
            raise ForbiddenException("Super Admin cannot access shopping list operations")

        result = await self.db.execute(
            select(ShoppingList).where(ShoppingList.id == list_id)
        )
        shopping_list = result.scalar_one_or_none()

        if not shopping_list:
            logger.warning("Shopping list not found for invitation")
            raise NotFoundException("Shopping list not found")

        if shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. No new invitations can be sent.")

        if shopping_list.tenant_id != inviter.tenant_id:
            logger.warning("Cross-tenant invitation access denied")
            raise ForbiddenException("Cross-tenant access denied")

        if inviter.role != UserRole.TENANT_ADMIN and shopping_list.owner_id != inviter.id:
            logger.warning("Unauthorized invitation attempt (not owner/admin)")
            raise ForbiddenException(
                "Only the list owner or tenant admin can send invitations"
            )

        result = await self.db.execute(
            select(User).where(
                and_(
                    User.id == user_id,
                    User.tenant_id == inviter.tenant_id,
                )
            )
        )
        invitee = result.scalar_one_or_none()

        if not invitee:
            logger.warning("Invitee user not found in tenant")
            raise NotFoundException("User not found in this tenant.")

        if not invitee.is_active:
            logger.warning("Attempted to invite inactive user")
            raise ValidationException("Cannot invite inactive user")

        if not invitee.is_email_verified:
            logger.warning("Attempted to invite unverified user")
            raise ValidationException("Cannot invite a user whose email is not verified")

        result = await self.db.execute(
            select(ShoppingListMember).where(
                and_(
                    ShoppingListMember.shopping_list_id == list_id,
                    ShoppingListMember.user_id == invitee.id,
                )
            )
        )
        if result.scalar_one_or_none():
            logger.info("User is already a member of this list")
            raise ConflictException("User is already a member of this list")

        result = await self.db.execute(
            select(ShoppingListInvite).where(
                and_(
                    ShoppingListInvite.shopping_list_id == list_id,
                    ShoppingListInvite.invited_user_id == invitee.id,
                    ShoppingListInvite.status == InviteStatus.PENDING,
                )
            )
        )
        if result.scalar_one_or_none():
            logger.info("Pending invitation already exists for this user")
            raise ConflictException("A pending invitation already exists for this user.")

        expires_delta = timedelta(hours=settings.INVITATION_TOKEN_EXPIRE_HOURS)
        token = create_invitation_token(
            list_id=list_id,
            email=invitee.email,
            tenant_id=inviter.tenant_id,
            inviter_id=inviter.id,
            expires_delta=expires_delta,
        )

        expires_at = get_now() + expires_delta

        invite = ShoppingListInvite(
            shopping_list_id=list_id,
            invited_user_id=invitee.id,
            invited_by_user_id=inviter.id,
            token=token,
            status=InviteStatus.PENDING,
            expires_at=expires_at,
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        
        logger.info("Invitation created")

        accept_url = f"{settings.INVITATION_BASE_URL}/accept?token={token}"
        reject_url = f"{settings.INVITATION_BASE_URL}/reject?token={token}"

        if background_tasks:
            logger.info("Staging invitation email background task")
            background_tasks.add_task(
                EmailService.send_invitation_email,
                to_email=invitee.email,
                inviter_name=inviter.username,
                list_name=shopping_list.name,
                accept_url=accept_url,
                reject_url=reject_url,
            )
        else:
            logger.info("Sending invitation email synchronously")
            await EmailService.send_invitation_email(
                to_email=invitee.email,
                inviter_name=inviter.username,
                list_name=shopping_list.name,
                accept_url=accept_url,
                reject_url=reject_url,
            )

        # Notify existing list members about the invitation
        notification_service = NotificationService(self.db)
        await notification_service.notify_list_members(
            list_id=list_id,
            notification_type=NotificationType.LIST_INVITE,
            payload={
                "invited_user": invitee.username,
                "invited_by": inviter.username,
                "list_name": shopping_list.name,
            },
            exclude_user_id=inviter.id,
        )

        return InviteResponse(
            message="Invitation sent successfully",
            expires_at=expires_at,
        )

    async def cancel_invitation(
        self, invite_id: UUID, user: User
    ) -> MessageResponse:
        """Cancel an invitation."""
        if user.role == UserRole.SUPER_ADMIN:
            logger.warning("Super Admin attempted shopping list operation")
            raise ForbiddenException("Super Admin cannot access shopping list operations")

        result = await self.db.execute(
            select(ShoppingListInvite)
            .options(selectinload(ShoppingListInvite.shopping_list))
            .where(ShoppingListInvite.id == invite_id)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            logger.warning("Invitation not found for cancellation")
            raise NotFoundException("Invitation not found")

        shopping_list = invite.shopping_list

        if shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. Invitations cannot be modified.")

        if shopping_list.tenant_id != user.tenant_id:
            logger.warning("Cross-tenant cancellation access denied")
            raise ForbiddenException("Cross-tenant access denied")

        if user.role != UserRole.TENANT_ADMIN and shopping_list.owner_id != user.id:
            logger.warning("Unauthorized cancellation attempt (not owner/admin)")
            raise ForbiddenException("Only the list owner or tenant admin can cancel invitations")

        if invite.status != InviteStatus.PENDING:
            logger.warning("Attempted to cancel non-pending invitation")
            raise MiniMartException(
                status_code=400,
                message=f"Cannot cancel — invitation is already {invite.status.value.lower()}.",
            )

        invite.status = InviteStatus.CANCELLED
        invite.cancelled_at = get_now()
        await self.db.commit()

        logger.info("Invitation cancelled")
        return MessageResponse(message="Invitation cancelled successfully")

    async def resend_invitation(
        self,
        invite_id: UUID,
        user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> InviteResponse:
        """Resend an invitation."""
        if user.role == UserRole.SUPER_ADMIN:
            logger.warning("Super Admin attempted shopping list operation")
            raise ForbiddenException("Super Admin cannot access shopping list operations")

        result = await self.db.execute(
            select(ShoppingListInvite)
            .options(
                selectinload(ShoppingListInvite.shopping_list),
                selectinload(ShoppingListInvite.invited_user),
            )
            .where(ShoppingListInvite.id == invite_id)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            logger.warning("Invitation not found for resend")
            raise NotFoundException("Invitation not found")

        shopping_list = invite.shopping_list

        if shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. Invitations cannot be resent.")

        if shopping_list.tenant_id != user.tenant_id:
            logger.warning("Cross-tenant resend access denied")
            raise ForbiddenException("Cross-tenant access denied")

        if user.role != UserRole.TENANT_ADMIN and shopping_list.owner_id != user.id:
            logger.warning("Unauthorized resend attempt (not owner/admin)")
            raise ForbiddenException("Only the list owner or tenant admin can resend invitations")

        if invite.status != InviteStatus.PENDING:
            logger.warning("Attempted to resend non-pending invitation")
            raise MiniMartException(
                status_code=400,
                message=f"Cannot resend — invitation is already {invite.status.value.lower()}.",
            )

        expires_delta = timedelta(hours=settings.INVITATION_TOKEN_EXPIRE_HOURS)
        new_token = create_invitation_token(
            list_id=invite.shopping_list_id,
            email=invite.invited_user.email,
            tenant_id=user.tenant_id,
            inviter_id=user.id,
            expires_delta=expires_delta,
        )

        invite.token = new_token
        invite.expires_at = get_now() + expires_delta
        invite.resent_at = get_now()
        await self.db.commit()

        logger.info("Invitation resent")

        accept_url = f"{settings.INVITATION_BASE_URL}/accept?token={new_token}"
        reject_url = f"{settings.INVITATION_BASE_URL}/reject?token={new_token}"

        if background_tasks:
            logger.info("Staging resent invitation email background task")
            background_tasks.add_task(
                EmailService.send_invitation_email,
                to_email=invite.invited_user.email,
                inviter_name=user.username,
                list_name=shopping_list.name,
                accept_url=accept_url,
                reject_url=reject_url,
            )
        else:
            logger.info("Sending resent invitation email synchronously")
            await EmailService.send_invitation_email(
                to_email=invite.invited_user.email,
                inviter_name=user.username,
                list_name=shopping_list.name,
                accept_url=accept_url,
                reject_url=reject_url,
            )

        return InviteResponse(
            message="Invitation resent successfully",
            expires_at=invite.expires_at,
        )

    async def get_list_invites(
        self,
        list_id: UUID,
        user: User,
        pagination: PaginationParams,
        status_filter: str | None = None,
    ) -> PaginatedResponse[InvitationResponse]:
        """Get invitations for a specific list."""
        if user.role == UserRole.SUPER_ADMIN:
            logger.warning("Super Admin attempted shopping list operation")
            raise ForbiddenException("Super Admin cannot access shopping list operations")

        result = await self.db.execute(
            select(ShoppingList).where(ShoppingList.id == list_id)
        )
        shopping_list = result.scalar_one_or_none()
        if not shopping_list:
            logger.warning("Shopping list not found for invitation retrieval")
            raise NotFoundException("Shopping list not found")

        if shopping_list.tenant_id != user.tenant_id:
            logger.warning("Cross-tenant invitation retrieval access denied")
            raise ForbiddenException("Cross-tenant access denied")

        if user.role != UserRole.TENANT_ADMIN and shopping_list.owner_id != user.id:
            logger.warning("Unauthorized invitation view attempt (not owner/admin)")
            raise ForbiddenException("Only the list owner or tenant admin can view invitations")
        query = select(ShoppingListInvite).options(
            selectinload(ShoppingListInvite.invited_user),
            selectinload(ShoppingListInvite.invited_by_user),
            selectinload(ShoppingListInvite.shopping_list),
        ).where(ShoppingListInvite.shopping_list_id == list_id)

        if status_filter and status_filter.upper() in InviteStatus.__members__:
            query = query.where(
                ShoppingListInvite.status == InviteStatus(status_filter.upper())
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(ShoppingListInvite.created_at.desc()).offset(pagination.skip).limit(pagination.size)
        result = await self.db.execute(query)
        invites = result.scalars().all()

        return PaginatedResponse(
            data=[InvitationResponse.model_validate(i) for i in invites],
            total=total,
            page=pagination.page,
            size=pagination.size
        )

    async def get_my_invites(
        self,
        user: User,
        pagination: PaginationParams,
        status_filter: str | None = None,
    ) -> PaginatedResponse[InvitationResponse]:
        """Get invitations sent to the current user."""
        self._block_super_admin(user)
        query = select(ShoppingListInvite).options(
            selectinload(ShoppingListInvite.shopping_list),
            selectinload(ShoppingListInvite.invited_by_user),
            selectinload(ShoppingListInvite.invited_user),
        ).where(ShoppingListInvite.invited_user_id == user.id)

        if status_filter and status_filter.upper() in InviteStatus.__members__:
            query = query.where(
                ShoppingListInvite.status == InviteStatus(status_filter.upper())
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(ShoppingListInvite.created_at.desc()).offset(pagination.skip).limit(pagination.size)
        result = await self.db.execute(query)
        invites = result.scalars().all()

        return PaginatedResponse(
            data=[InvitationResponse.model_validate(i) for i in invites],
            total=total,
            page=pagination.page,
            size=pagination.size
        )
