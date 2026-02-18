"""
Chat Service

"""

from datetime import datetime
from typing import Any
from uuid import UUID


from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.constants import WS_EVENT_CHAT_MESSAGE
from app.core.pagination import PaginationParams
from app.common.enums import UserRole
from app.core.logging import get_logger
from app.core.time import get_now
from app.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.chat_message import ChatMessage
from app.models.shopping_list import ShoppingList
from app.models.shopping_list_member import ShoppingListMember
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.chat import ChatMessageResponse
from app.websocket.manager import manager

logger = get_logger(__name__)



class ChatService:
    """Service for list-scoped chat operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _verify_membership(
        self, list_id: UUID, user: User
    ) -> ShoppingListMember:
        """
        Verify the user is an ACCEPTED member of the list.
        """
        if user.role == UserRole.SUPER_ADMIN:
            raise ForbiddenException("Super Admin cannot access shopping list chat")

        if user.role == UserRole.TENANT_ADMIN:
            result = await self.db.execute(
                select(ShoppingList).where(ShoppingList.id == list_id)
            )
            shopping_list = result.scalar_one_or_none()
            if not shopping_list:
                raise NotFoundException("Shopping list not found")
            if shopping_list.tenant_id != user.tenant_id:
                raise ForbiddenException("Cross-tenant access denied")
            return None

        result = await self.db.execute(
            select(ShoppingListMember).where(
                and_(
                    ShoppingListMember.shopping_list_id == list_id,
                    ShoppingListMember.user_id == user.id,
                    ShoppingListMember.deleted_at.is_(None),
                )
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise ForbiddenException("You are not a member of this list")

        return membership

    async def send_message(
        self, list_id: UUID, user: User, content: str
    ) -> dict[str, Any]:
        """
        Send a chat message to a shopping list.
        Validates membership, persists, and broadcasts.
        """
        if not content or not content.strip():
            raise ValidationException("Message content cannot be empty")

        # Check if list is deleted
        result = await self.db.execute(
            select(ShoppingList).where(ShoppingList.id == list_id)
        )
        shopping_list = result.scalar_one_or_none()
        if shopping_list and shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted.")

        await self._verify_membership(list_id, user)

        message = ChatMessage(
            shopping_list_id=list_id,
            sender_id=user.id,
            content=content.strip(),
        )
        self.db.add(message)
        try:
            await self.db.commit()
            await self.db.refresh(message)
        except Exception:
            logger.error("Chat message commit failed")
            await self.db.rollback()
            raise

        broadcast_payload = {
            "id": str(message.id),
            "type": WS_EVENT_CHAT_MESSAGE,
            "shopping_list_id": str(list_id),
            "sender_id": str(user.id),
            "sender_name": user.username,
            "message": message.content,
            "created_at": message.created_at.isoformat(),
        }

        await manager.broadcast_chat(
            str(list_id),
            broadcast_payload,
            exclude_user_id=None
        )
        logger.info("Chat message sent")

        return broadcast_payload

    async def get_messages(
        self,
        list_id: UUID,
        user: User,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ChatMessageResponse]:
        """
        Load chat history for a shopping list (Newest First).
        """
        await self._verify_membership(list_id, user)

        # Count total messages
        count_query = select(func.count(ChatMessage.id)).where(
            and_(
                ChatMessage.shopping_list_id == list_id,
                ChatMessage.deleted_at.is_(None),
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        query = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.sender))
            .where(
                and_(
                    ChatMessage.shopping_list_id == list_id,
                    ChatMessage.deleted_at.is_(None),
                )
            )
        )

        query = query.order_by(ChatMessage.created_at.desc()).offset(pagination.skip).limit(pagination.size)
        result = await self.db.execute(query)
        messages = result.scalars().all()

        items = [
            ChatMessageResponse(
                id=m.id,
                shopping_list_id=m.shopping_list_id,
                sender_id=m.sender_id,
                sender_name=m.sender.username if m.sender else "Unknown",
                message=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ]
        return PaginatedResponse(
            data=items,
            total=total,
            page=pagination.page,
            size=pagination.size
        )


    async def delete_message(
        self, list_id: UUID, message_id: UUID, user: User
    ) -> None:
        """
        Soft-delete a chat message.
        Only the sender or list owner can delete.
        """
        result = await self.db.execute(
            select(ShoppingList).where(ShoppingList.id == list_id)
        )
        shopping_list = result.scalar_one_or_none()
        if shopping_list and shopping_list.deleted_at:
            raise ForbiddenException("This list is deleted. ")

        await self._verify_membership(list_id, user)

        result = await self.db.execute(
            select(ChatMessage).where(
                and_(
                    ChatMessage.id == message_id,
                    ChatMessage.shopping_list_id == list_id,
                    ChatMessage.deleted_at.is_(None),
                )
            )
        )
        message = result.scalar_one_or_none()
        if not message:
            raise NotFoundException("Message not found")

        is_sender = message.sender_id == user.id
        is_tenant_admin = user.role == UserRole.TENANT_ADMIN

        is_owner = False
        if not is_sender and not is_tenant_admin:
            result = await self.db.execute(
                select(ShoppingList).where(ShoppingList.id == list_id)
            )
            shopping_list = result.scalar_one_or_none()
            if shopping_list and shopping_list.owner_id == user.id:
                is_owner = True

        if not is_sender and not is_owner and not is_tenant_admin:
            raise ForbiddenException("Only the message sender or list owner can delete messages")

        message.deleted_at = get_now()
        await self.db.commit()
        logger.info("Chat message deleted")
