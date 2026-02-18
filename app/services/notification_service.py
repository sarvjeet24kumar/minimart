"""
Notification Service
"""

import uuid
from typing import Any


from sqlalchemy import and_, desc, func, not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.common.enums import NotificationType
from app.core.logging import get_logger
from app.exceptions import NotFoundException
from app.models.notification import Notification
from app.models.shopping_list_member import ShoppingListMember
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.notification import NotificationResponse
from app.websocket.manager import manager

logger = get_logger(__name__)


class NotificationService:
    """Service for handling notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        payload: dict[str, Any],
        shopping_list_id: uuid.UUID | None = None,
        send_websocket: bool = True,
    ) -> Notification:
        """
        Create a notification in the database and dispatch via WebSocket.
        """
        notification = Notification(
            user_id=user_id,
            shopping_list_id=shopping_list_id,
            type=notification_type,
            payload=payload,
            is_read=False,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # Dispatch via WebSocket (real-time)
        if send_websocket:
            try:
                await manager.send_notification_to_user(
                    str(user_id),
                    {
                        "type": "notification",
                        "payload": {
                            "id": str(notification.id),
                            "type": notification_type.value,
                            "data": notification.payload,
                            "list_id": str(notification.shopping_list_id) if notification.shopping_list_id else None,
                            "created_at": notification.created_at.isoformat(),
                        },
                    },
                )
            except Exception as e:
                logger.error(f"Failed to dispatch WebSocket notification: {e}")

        return notification

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        pagination: PaginationParams,
        is_read: bool | None = None,
    ) -> PaginatedResponse[NotificationResponse]:
        """
        Get paginated notifications for a user with optional filter.
        """
        base_filter = Notification.user_id == user_id
        query = select(Notification).where(base_filter)
        count_query = select(func.count(Notification.id)).where(base_filter)

        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
            count_query = count_query.where(Notification.is_read == is_read)

        query = query.order_by(desc(Notification.created_at)).offset(pagination.skip).limit(pagination.size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return PaginatedResponse(
            data=[NotificationResponse.model_validate(i) for i in items],
            total=total,
            page=pagination.page,
            size=pagination.size
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get the count of unread notifications for a user."""
        query = select(func.count(Notification.id)).where(
            and_(Notification.user_id == user_id, not_(Notification.is_read))
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> MessageResponse:
        """Mark a specific notification as read."""
        query = (
            update(Notification)
            .where(and_(Notification.id == notification_id, Notification.user_id == user_id))
            .values(is_read=True)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        if result.rowcount == 0:
            raise NotFoundException("Notification not found")
        
        return MessageResponse(message="Notification marked as read")

    async def mark_all_as_read(self, user_id: uuid.UUID) -> MessageResponse:
        """Mark all notifications for a user as read."""
        query = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, not_(Notification.is_read)))
            .values(is_read=True)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        
        count = result.rowcount
        return MessageResponse(message=f"Marked {count} notifications as read")

    async def notify_list_members(
        self,
        list_id: uuid.UUID,
        notification_type: NotificationType,
        payload: dict[str, Any],
        exclude_user_id: uuid.UUID | None = None,
        skip_dedup: bool = False,
    ) -> int:
        """
        Notify all members of a shopping list about an event.
        """
        result = await self.db.execute(
            select(ShoppingListMember.user_id).where(
                and_(
                    ShoppingListMember.shopping_list_id == list_id,
                    ShoppingListMember.deleted_at.is_(None),
                )
            )
        )
        member_ids = result.scalars().all()
        
        count = 0
        for user_id in member_ids:
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            await self.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                payload=payload,
                shopping_list_id=None if skip_dedup else list_id,
                send_websocket=True,
            )
            count += 1
            
        return count
