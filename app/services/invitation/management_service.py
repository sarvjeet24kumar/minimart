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
from app.core.security import create_invitation_token, decode_invitation_token
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
from app.services.redis_service import RedisService

logger = get_logger(__name__)

class InvitationManagementService(BaseService):
    """Handles creation and administrative management of invitations."""

    async def _get_list_with_access(self, list_id: UUID, user: User) -> ShoppingList:
        """Fetch list and check access (owner/admin/tenant)."""
        self._block_super_admin(user)
        result = await self.db.execute(select(ShoppingList).where(ShoppingList.id == list_id))
        shopping_list = result.scalar_one_or_none()

        if not shopping_list:
            logger.warning(f"Shopping list {list_id} not found")
            raise NotFoundException("Shopping list not found")

        if shopping_list.tenant_id != user.tenant_id:
            logger.warning(f"Cross-tenant access denied for user {user.id}")
            raise ForbiddenException("Cross-tenant access denied")

        if user.role != UserRole.TENANT_ADMIN and shopping_list.owner_id != user.id:
            logger.warning(f"Unauthorized access to list {list_id} by user {user.id}")
            raise ForbiddenException("Only the list owner or tenant admin can manage invitations")

        return shopping_list

    async def _get_invite_with_access(self, invite_id: UUID, user: User) -> ShoppingListInvite:
        """Fetch invite and check access via parent list."""
        result = await self.db.execute(
            select(ShoppingListInvite)
            .options(selectinload(ShoppingListInvite.shopping_list))
            .where(ShoppingListInvite.id == invite_id)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            logger.warning(f"Invitation {invite_id} not found")
            raise NotFoundException("Invitation not found")

        # Reuse list access logic
        await self._get_list_with_access(invite.shopping_list_id, user)
        return invite

    async def _process_token_and_email(
        self,
        invite_id: UUID,
        list_id: UUID,
        list_name: str,
        invitee_email: str,
        inviter: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> tuple[str, datetime]:
        """Generate token, store in Redis, and send email."""
        expires_delta = timedelta(hours=settings.INVITATION_TOKEN_EXPIRE_HOURS)
        token = create_invitation_token(
            invite_id=invite_id,
            list_id=list_id,
            email=invitee_email,
            tenant_id=inviter.tenant_id,
            inviter_id=inviter.id,
            expires_delta=expires_delta,
        )
        expires_at = get_now() + expires_delta

        # Redis storage
        payload = decode_invitation_token(token)
        await RedisService.store_invitation_token(
            token_id=payload["jti"],
            list_id=str(list_id),
            expire_seconds=int(expires_delta.total_seconds()),
        )

        # Email sending
        accept_url = f"{settings.INVITATION_BASE_URL}/accept?token={token}"
        reject_url = f"{settings.INVITATION_BASE_URL}/reject?token={token}"

        if background_tasks:
            background_tasks.add_task(
                EmailService.send_invitation_email,
                to_email=invitee_email,
                inviter_name=inviter.username,
                list_name=list_name,
                accept_url=accept_url,
                reject_url=reject_url,
            )
        else:
            await EmailService.send_invitation_email(
                to_email=invitee_email,
                inviter_name=inviter.username,
                list_name=list_name,
                accept_url=accept_url,
                reject_url=reject_url,
            )
        
        return token, expires_at

    async def send_invitation(
        self,
        list_id: UUID,
        user_id: UUID,
        inviter: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> InviteResponse:
        """Create a DB-backed invitation to join a shopping list."""
        shopping_list = await self._get_list_with_access(list_id, inviter)

        if shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. No new invitations can be sent.")

        # Resolve Invitee
        result = await self.db.execute(
            select(User).where(and_(User.id == user_id, User.tenant_id == inviter.tenant_id))
        )
        invitee = result.scalar_one_or_none()

        if not invitee or not invitee.is_active or not invitee.is_email_verified:
            logger.warning(f"Invalid invitee {user_id}")
            raise ValidationException("Invitee not found, inactive, or unverified")

        # Check existing membership
        result = await self.db.execute(
            select(ShoppingListMember).where(
                and_(ShoppingListMember.shopping_list_id == list_id, ShoppingListMember.user_id == invitee.id)
            )
        )
        if result.scalar_one_or_none():
            raise ConflictException("User is already a member of this list")

        # Check duplicate pending invite
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
            raise ConflictException("A pending invitation already exists for this user.")

        # Create Record First (to get ID)
        expires_delta = timedelta(hours=settings.INVITATION_TOKEN_EXPIRE_HOURS)
        expires_at = get_now() + expires_delta
        
        invite = ShoppingListInvite(
            shopping_list_id=list_id,
            invited_user_id=invitee.id,
            invited_by_user_id=inviter.id,
            status=InviteStatus.PENDING,
            expires_at=expires_at,
        )
        self.db.add(invite)
        await self.db.flush()  # Get the ID

        # Process Token & Email with Record ID
        await self._process_token_and_email(
            invite.id, list_id, shopping_list.name, invitee.email, inviter, background_tasks
        )
        await self.db.commit()
        
        # Internal Notification
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

        return InviteResponse(message="Invitation sent successfully", expires_at=expires_at)

    async def cancel_invitation(self, invite_id: UUID, user: User) -> MessageResponse:
        """Cancel an invitation."""
        invite = await self._get_invite_with_access(invite_id, user)

        if invite.shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. Invitations cannot be modified.")

        if invite.status != InviteStatus.PENDING:
            raise MiniMartException(
                status_code=400,
                message=f"Cannot cancel — invitation is already {invite.status.value.lower()}.",
            )

        # Update DB
        invite.status = InviteStatus.CANCELLED
        invite.cancelled_at = get_now()
        await self.db.commit()

        # Note: Since we don't store the token in the DB, we cannot get its jti 
        # to invalidate it in Redis here. However, the DB status check in 
        # ActionService will prevent any existing tokens from being used.

        return MessageResponse(message="Invitation cancelled successfully")

    async def resend_invitation(
        self, invite_id: UUID, user: User, background_tasks: BackgroundTasks | None = None
    ) -> InviteResponse:
        """Resend an invitation."""
        result = await self.db.execute(
            select(ShoppingListInvite)
            .options(selectinload(ShoppingListInvite.invited_user))
            .where(ShoppingListInvite.id == invite_id)
        )
        invite = result.scalar_one_or_none()
        if not invite:
             raise NotFoundException("Invitation not found")

        # Check access (reuses list check)
        shopping_list = await self._get_list_with_access(invite.shopping_list_id, user)

        if shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. Invitations cannot be resent.")

        if invite.status != InviteStatus.PENDING:
            raise MiniMartException(
                status_code=400,
                message=f"Cannot resend — invitation is already {invite.status.value.lower()}.",
            )

        # 1. Cancel the old record (Invalidates the old token ID)
        invite.status = InviteStatus.CANCELLED
        invite.cancelled_at = get_now()
        
        # 2. Create a fresh record (Gives us a new ID for the new token)
        expires_delta = timedelta(hours=settings.INVITATION_TOKEN_EXPIRE_HOURS)
        expires_at = get_now() + expires_delta
        
        new_invite = ShoppingListInvite(
            shopping_list_id=invite.shopping_list_id,
            invited_user_id=invite.invited_user_id,
            invited_by_user_id=user.id,
            status=InviteStatus.PENDING,
            expires_at=expires_at,
        )
        self.db.add(new_invite)
        await self.db.flush()

        # 3. Create New Token & Notify using the NEW ID
        await self._process_token_and_email(
            new_invite.id, shopping_list.id, shopping_list.name, invite.invited_user.email, user, background_tasks
        )

        await self.db.commit()

        return InviteResponse(message="Invitation resent successfully", expires_at=expires_at)

    async def get_list_invites(
        self, list_id: UUID, user: User, pagination: PaginationParams, status_filter: str | None = None
    ) -> PaginatedResponse[InvitationResponse]:
        """Get invitations for a specific list."""
        await self._get_list_with_access(list_id, user)

        query = select(ShoppingListInvite).options(
            selectinload(ShoppingListInvite.invited_user),
            selectinload(ShoppingListInvite.invited_by_user),
            selectinload(ShoppingListInvite.shopping_list),
        ).where(ShoppingListInvite.shopping_list_id == list_id)

        if status_filter and status_filter.upper() in InviteStatus.__members__:
            query = query.where(ShoppingListInvite.status == InviteStatus(status_filter.upper()))

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(ShoppingListInvite.created_at.desc()).offset(pagination.skip).limit(pagination.size)
        result = await self.db.execute(query)
        invites = result.scalars().all()

        return PaginatedResponse(
            data=[InvitationResponse.model_validate(i) for i in invites],
            total=total,
            page=pagination.page,
            size=pagination.size,
        )

    async def get_my_invites(
        self, user: User, pagination: PaginationParams, status_filter: str | None = None
    ) -> PaginatedResponse[InvitationResponse]:
        """Get invitations sent to the current user."""
        self._block_super_admin(user)
        query = select(ShoppingListInvite).options(
            selectinload(ShoppingListInvite.shopping_list),
            selectinload(ShoppingListInvite.invited_by_user),
            selectinload(ShoppingListInvite.invited_user),
        ).where(ShoppingListInvite.invited_user_id == user.id)

        if status_filter and status_filter.upper() in InviteStatus.__members__:
            query = query.where(ShoppingListInvite.status == InviteStatus(status_filter.upper()))

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(ShoppingListInvite.created_at.desc()).offset(pagination.skip).limit(pagination.size)
        result = await self.db.execute(query)
        invites = result.scalars().all()

        return PaginatedResponse(
            data=[InvitationResponse.model_validate(i) for i in invites],
            total=total,
            page=pagination.page,
            size=pagination.size,
        )
