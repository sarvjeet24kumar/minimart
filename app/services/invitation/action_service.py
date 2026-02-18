"""
Invitation Action Service
"""

from uuid import UUID

from jose import JWTError
from sqlalchemy import and_, select

from app.common.enums import InviteAction, InviteStatus, MemberRole, NotificationType
from app.core.logging import get_logger
from app.core.security import decode_invitation_token
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
from app.schemas.common import MessageResponse
from app.services.base import BaseService
from app.services.notification_service import NotificationService
from app.services.redis_service import RedisService


logger = get_logger(__name__)


class InvitationActionService(BaseService):
    """Handles accepting and rejecting invitations."""

    async def respond_to_invitation(self, token: str, action: InviteAction, user: User) -> MessageResponse:
        """Respond to an invitation (accept or reject)."""
        if action == InviteAction.ACCEPT:
            await self.accept_invitation(token, user)
            return MessageResponse(message="Invitation accepted")
        else:
            await self.reject_invitation(token, user)
            return MessageResponse(message="Invitation rejected")

    async def _get_valid_invite(self, token: str, user: User) -> tuple[ShoppingListInvite, dict]:
        """Internal helper to validate token and fetch a pending invitation."""
        self._block_super_admin(user)
        try:
            payload = decode_invitation_token(token)
        except JWTError as e:
            logger.warning("Invalid or expired invitation token")
            raise ValidationException(f"Invalid or expired invitation token: {str(e)}") from e

        if payload["email"] != user.email:
            logger.warning("Invitation email mismatch")
            raise ForbiddenException("Invalid Token")

        if UUID(payload["tenant_id"]) != user.tenant_id:
            logger.warning("Cross-tenant invitation attempt denied")
            raise ForbiddenException("Cross-tenant invitation not allowed")

        # Lookup by unique invitation ID from payload
        result = await self.db.execute(
            select(ShoppingListInvite).where(
                ShoppingListInvite.id == UUID(payload["invite_id"])
            )
        )
        invite = result.scalar_one_or_none()

        if not invite:
            logger.warning("Invitation record not found")
            raise ValidationException("Invitation not found")

        if invite.status != InviteStatus.PENDING:
            logger.warning(f"Attempted to process non-pending invitation: {invite.status}")
            raise MiniMartException(
                status_code=400,
                message=f"Invitation has already been {invite.status.value.lower()}.",
            )

        if invite.expires_at < get_now():
            logger.info("Invitation has expired")
            invite.status = InviteStatus.EXPIRED
            await self.db.commit()
            await RedisService.invalidate_invitation_token(payload["jti"])
            raise ValidationException("Invitation has expired")

        # Redis Validation (Single-use enforcement)
        if not await RedisService.validate_invitation_token(payload["jti"]):
            logger.warning("Invitation token not found in Redis or already used")
            raise ValidationException("Invitation token is invalid or has already been used")

        return invite, payload

    async def accept_invitation(self, token: str, user: User) -> ShoppingList:
        """Accept an invitation."""
        invite, payload = await self._get_valid_invite(token, user)
        list_id = invite.shopping_list_id

        result = await self.db.execute(
            select(ShoppingList).where(ShoppingList.id == list_id)
        )
        shopping_list = result.scalar_one_or_none()

        if not shopping_list:
            logger.warning("Shopping list not found for invitation acceptance")
            raise NotFoundException("Shopping list no longer exists")

        if shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. You cannot join it.")

        # Check existing membership
        result = await self.db.execute(
            select(ShoppingListMember).where(
                and_(
                    ShoppingListMember.shopping_list_id == list_id,
                    ShoppingListMember.user_id == user.id,
                )
            )
        )
        if result.scalar_one_or_none():
            invite.status = InviteStatus.ACCEPTED
            invite.accepted_at = get_now()
            await self.db.commit()
            await RedisService.invalidate_invitation_token(payload["jti"])
            raise ConflictException("User is already a member of this list")

        membership = ShoppingListMember(
            shopping_list_id=list_id,
            user_id=user.id,
            role=MemberRole.MEMBER,
        )
        self.db.add(membership)

        invite.status = InviteStatus.ACCEPTED
        invite.accepted_at = get_now()
        await self.db.commit()
        await RedisService.invalidate_invitation_token(payload["jti"])

        # Notify existing list members
        notification_service = NotificationService(self.db)
        await notification_service.notify_list_members(
            list_id=list_id,
            notification_type=NotificationType.INVITE_ACCEPTED,
            payload={"user": user.username, "list_name": shopping_list.name},
            exclude_user_id=user.id,
        )

        logger.info("Invitation accepted successfully")
        await self.db.refresh(shopping_list)
        return shopping_list

    async def reject_invitation(self, token: str, user: User) -> bool:
        """Reject an invitation."""
        try:
            invite, payload = await self._get_valid_invite(token, user)
        except (ValidationException, ForbiddenException, MiniMartException):
            # For reject, we can be more lenient if it's already processed or invalid
            logger.info("Skipping rejection: Token already processed or invalid")
            return True

        invite.status = InviteStatus.REJECTED
        invite.rejected_at = get_now()
        await self.db.commit()
        await RedisService.invalidate_invitation_token(payload["jti"])

        # Notify existing list members
        result = await self.db.execute(
            select(ShoppingList).where(ShoppingList.id == invite.shopping_list_id)
        )
        shopping_list = result.scalar_one_or_none()
        if shopping_list:
            notification_service = NotificationService(self.db)
            await notification_service.notify_list_members(
                list_id=invite.shopping_list_id,
                notification_type=NotificationType.INVITE_REJECTED,
                payload={"user": user.username, "list_name": shopping_list.name},
                exclude_user_id=user.id,
            )

        logger.info("Invitation rejected successfully")
        return True
