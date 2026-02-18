"""
Tenant Service

Handles tenant creation and management (Super Admin operations).
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.constants import DEFAULT_PAGE_SIZE
from app.core.logging import get_logger
from app.exceptions import ConflictException, NotFoundException
from app.models.tenant import Tenant
from app.models.user import User
from app.models.shopping_list import ShoppingList
from app.models.item import Item
from app.schemas.tenant import TenantCreate, TenantUpdate

logger = get_logger(__name__)


class TenantService:
    """Service for tenant management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        """
        Create a new tenant.
        """
        result = await self.db.execute(select(Tenant).where(Tenant.slug == data.slug))
        if result.scalar_one_or_none():
            logger.info("Tenant creation failed: Slug already exists")
            raise ConflictException("Slug already exists")

        tenant = Tenant(
            **data.model_dump(),
            is_active=True,
        )
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        logger.info("New tenant created successfully")
        return tenant

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Get a tenant by ID with counts.
        """
        # Fetch tenant
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.warning("Tenant not found")
            raise NotFoundException("Tenant not found")

        # Fetch counts
        user_count = await self.db.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant_id)
        )
        list_count = await self.db.execute(
            select(func.count(ShoppingList.id)).where(ShoppingList.tenant_id == tenant_id)
        )
        item_count = await self.db.execute(
            select(func.count(Item.id))
            .join(ShoppingList, Item.shopping_list_id == ShoppingList.id)
            .where(ShoppingList.tenant_id == tenant_id)
        )

        # Attach counts to tenant object for the schema to pick up
        tenant.total_users = user_count.scalar_one()
        tenant.total_lists = list_count.scalar_one()
        tenant.total_items = item_count.scalar_one()

        return tenant

    async def get_all_tenants(
        self, skip: int = 0, limit: int = DEFAULT_PAGE_SIZE
    ) -> tuple[list[Tenant], int]:
        """
        Get all tenants with pagination and counts.
        """
        # Total count for pagination
        count_result = await self.db.execute(select(func.count()).select_from(Tenant))
        total = count_result.scalar_one()

        # Fetch tenants
        result = await self.db.execute(select(Tenant).offset(skip).limit(limit))
        tenants = list(result.scalars().all())

        # For each tenant, fetch counts (simplified for now, can be optimized with subqueries if needed)
        for tenant in tenants:
            user_count = await self.db.execute(
                select(func.count(User.id)).where(User.tenant_id == tenant.id)
            )
            list_count = await self.db.execute(
                select(func.count(ShoppingList.id)).where(ShoppingList.tenant_id == tenant.id)
            )
            item_count = await self.db.execute(
                select(func.count(Item.id))
                .join(ShoppingList, Item.shopping_list_id == ShoppingList.id)
                .where(ShoppingList.tenant_id == tenant.id)
            )
            
            tenant.total_users = user_count.scalar_one()
            tenant.total_lists = list_count.scalar_one()
            tenant.total_items = item_count.scalar_one()

        return tenants, total

    async def update_tenant(self, tenant_id: UUID, data: TenantUpdate) -> Tenant:
        tenant = await self.get_tenant(tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        if "slug" in update_data and update_data["slug"] != tenant.slug:
            result = await self.db.execute(
                select(Tenant).where(Tenant.slug == update_data["slug"])
            )
            if result.scalar_one_or_none():
                logger.info("Tenant update failed: New slug already exists")
                raise ConflictException("Slug already exists")

        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.commit()
        await self.db.refresh(tenant)
        logger.info("Tenant updated successfully")
        return tenant

    async def delete_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Soft delete a tenant.
        """
        tenant = await self.get_tenant(tenant_id)
        if tenant.deleted_at:
            logger.info("Tenant deletion failed: Already deleted")
            raise ConflictException("Tenant already deleted")

        tenant.deleted_at = func.now()
        tenant.is_active = False
        await self.db.commit()
        await self.db.refresh(tenant)
        logger.info("Tenant deactivated successfully")
        return tenant
