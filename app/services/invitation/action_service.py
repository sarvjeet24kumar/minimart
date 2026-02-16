"""
Invitation Action Service
"""

from uuid import UUID

from jose import JWTError
from sqlalchemy import and_, select

from app.common.enums import InviteStatus, MemberRole, NotificationType
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
from app.services.invitation.base import BaseInvitationService
from app.services.notification_service import NotificationService


class InvitationActionService(BaseInvitationService):
    """Handles accepting and rejecting invitations."""

    async def accept_invitation(self, token: str, user: User) -> ShoppingList:
        """Accept an invitation."""
        try:
            payload = decode_invitation_token(token)
        except JWTError as e:
            raise ValidationException(f"Invalid or expired invitation token: {str(e)}") from e

        if payload["email"] != user.email:
            raise ForbiddenException("Invalid Token")

        if UUID(payload["tenant_id"]) != user.tenant_id:
            raise ForbiddenException("Cross-tenant invitation not allowed")

        result = await self.db.execute(
            select(ShoppingListInvite).where(ShoppingListInvite.token == token)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            raise ValidationException("Invitation not found")

        if invite.status != InviteStatus.PENDING:
            raise MiniMartException(
                status_code=400,
                code="INVITE_NOT_PENDING",
                message=f"Invitation has already been {invite.status.value.lower()}.",
            )

        if invite.expires_at < get_now():
            invite.status = InviteStatus.EXPIRED
            await self.db.commit()
            raise ValidationException("Invitation has expired")

        list_id = invite.shopping_list_id

        result = await self.db.execute(
            select(ShoppingList).where(ShoppingList.id == list_id)
        )
        shopping_list = result.scalar_one_or_none()

        if not shopping_list:
            raise NotFoundException("Shopping list no longer exists")

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

        await self._broadcast(list_id, "member_joined", {
            "user_id": str(user.id),
            "username": user.username,
            "role": MemberRole.MEMBER.value,
        }, exclude_user_id=user.id)

        notification_service = NotificationService(self.db)
        await notification_service.create_notification(
            user_id=invite.invited_by_user_id,
            notification_type=NotificationType.INVITE_ACCEPTED,
            payload={
                "username": user.username,
                "list_name": shopping_list.name,
            },
            shopping_list_id=list_id,
        )

        await self.db.refresh(shopping_list)
        return shopping_list

    async def reject_invitation(self, token: str) -> bool:
        """Reject an invitation."""
        try:
            decode_invitation_token(token)
        except JWTError:
            return True

        result = await self.db.execute(
            select(ShoppingListInvite).where(ShoppingListInvite.token == token)
        )
        invite = result.scalar_one_or_none()

        if not invite or invite.status != InviteStatus.PENDING:
            return True

        if invite.expires_at < get_now():
            invite.status = InviteStatus.EXPIRED
            await self.db.commit()
            return True

        invite.status = InviteStatus.REJECTED
        invite.rejected_at = get_now()
        await self.db.commit()

        await self._broadcast(invite.shopping_list_id, "invite_rejected", {
            "invite_id": str(invite.id),
            "invited_user_id": str(invite.invited_user_id),
        })

        notification_service = NotificationService(self.db)
        await notification_service.create_notification(
            user_id=invite.invited_by_user_id,
            notification_type=NotificationType.INVITE_REJECTED,
            payload={
                "username": "Someone",
                "invite_id": str(invite.id),
            },
            shopping_list_id=invite.shopping_list_id,
        )

        return True
