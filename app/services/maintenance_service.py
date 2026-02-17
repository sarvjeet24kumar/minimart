"""
Maintenance Service
"""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.time import get_now
from app.models.chat_message import ChatMessage
from app.models.item import Item
from app.models.notification import Notification
from app.models.shopping_list import ShoppingList
from app.models.shopping_list_member import ShoppingListMember
from app.models.tenant import Tenant
from app.models.user import User

logger = get_logger(__name__)


class MaintenanceService:
    """Service for periodic database maintenance."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def hard_delete_unverified_users(self) -> int:
        """
        Hard delete users who haven't verified their email within the retention period.
        """
        threshold = get_now() - timedelta(hours=settings.USER_UNVERIFIED_RETENTION_HOURS)
        
        stmt = select(User).where(
            and_(
                User.is_email_verified == False,
                User.created_at < threshold
            )
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        count = len(users)

        if count > 0:
            delete_stmt = delete(User).where(
                and_(
                    User.is_email_verified == False,
                    User.created_at < threshold
                )
            )
            await self.db.execute(delete_stmt)
            await self.db.commit()
            logger.info("Maintenance: Hard deleted %d unverified users.", count)
        
        return count

    async def erase_deleted_user_data(self) -> int:
        """
        Erase activity data for users who have been soft-deleted beyond the retention period.
        The user account remains but their data is wiped.
        """
        threshold = get_now() - timedelta(days=settings.USER_DATA_RETENTION_DAYS)
        
        stmt = select(User).where(
            and_(
                User.deleted_at.is_not(None),
                User.deleted_at < threshold
            )
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        
        total_wiped = 0
        for user in users:
            
            await self.db.execute(delete(ShoppingList).where(ShoppingList.owner_id == user.id))
            
            await self.db.execute(delete(Item).where(Item.added_by == user.id))
            
            await self.db.execute(delete(ChatMessage).where(ChatMessage.sender_id == user.id))
            
            await self.db.execute(delete(Notification).where(Notification.user_id == user.id))
            
            await self.db.execute(delete(ShoppingListMember).where(ShoppingListMember.user_id == user.id))

            total_wiped += 1
            
        if total_wiped > 0:
            await self.db.commit()
            logger.info("Maintenance: Erased data for %d soft-deleted users.", total_wiped)
            
        return total_wiped

    async def hard_delete_expired_tenants(self) -> int:
        """
        Permanently delete tenants who have been soft-deleted beyond the retention period.
        """
        threshold = get_now() - timedelta(days=settings.TENANT_RETENTION_DAYS)
        
        stmt = select(Tenant).where(
            and_(
                Tenant.deleted_at.is_not(None),
                Tenant.deleted_at < threshold
            )
        )
        result = await self.db.execute(stmt)
        tenants = result.scalars().all()
        count = len(tenants)

        if count > 0:
            delete_stmt = delete(Tenant).where(
                and_(
                    Tenant.deleted_at.is_not(None),
                    Tenant.deleted_at < threshold
                )
            )
            await self.db.execute(delete_stmt)
            await self.db.commit()
            logger.info("Maintenance: Hard deleted %d expired tenants.", count)
            
        return count
