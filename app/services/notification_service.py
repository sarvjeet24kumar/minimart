"""
Notification Service
"""

import uuid
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, desc, func, not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import DEFAULT_PAGE_SIZE
from app.common.enums import NotificationType
from app.core.config import settings
from app.core.logging import get_logger
from app.models.notification import Notification
from app.models.shopping_list_member import ShoppingListMember
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
                            "created_at": notification.created_at.astimezone(ZoneInfo(settings.TIMEZONE)).isoformat(),
                        },
                    },
                )
            except Exception as e:
                logger.error(f"Failed to dispatch WebSocket notification: {e}")

        return notification

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        is_read: bool | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        skip: int = 0,
    ) -> list[Notification]:
        """
        Get paginated notifications for a user with optional filter.
        """
        query = select(Notification).where(Notification.user_id == user_id)
        
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        
        query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get the count of unread notifications for a user."""
        query = select(func.count(Notification.id)).where(
            and_(Notification.user_id == user_id, not_(Notification.is_read))
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Mark a specific notification as read."""
        query = (
            update(Notification)
            .where(and_(Notification.id == notification_id, Notification.user_id == user_id))
            .values(is_read=True)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications for a user as read."""
        query = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, not_(Notification.is_read)))
            .values(is_read=True)
        )
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount

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
