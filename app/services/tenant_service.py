"""
Tenant Service

Handles tenant creation and management (Super Admin operations).
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictException, NotFoundException
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


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
            raise ConflictException("Slug already exists")

        tenant = Tenant(
            **data.model_dump(),
            is_active=True,
        )
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Get a tenant by ID.
        """
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundException("Tenant not found")

        return tenant

    async def get_all_tenants(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[Tenant], int]:
        """
        Get all tenants with pagination.
        """
        count_result = await self.db.execute(select(func.count()).select_from(Tenant))
        total = count_result.scalar_one()

        result = await self.db.execute(select(Tenant).offset(skip).limit(limit))
        items = list(result.scalars().all())

        return items, total

    async def update_tenant(self, tenant_id: UUID, data: TenantUpdate) -> Tenant:
        tenant = await self.get_tenant(tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        if "slug" in update_data and update_data["slug"] != tenant.slug:
            result = await self.db.execute(
                select(Tenant).where(Tenant.slug == update_data["slug"])
            )
            if result.scalar_one_or_none():
                raise ConflictException("Slug already exists")

        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def delete_tenant(self, tenant_id: UUID) -> Tenant:
        """
        Soft delete a tenant.
        """
        tenant = await self.get_tenant(tenant_id)
        if tenant.deleted_at:
            raise ConflictException("Tenant already deleted")

        tenant.deleted_at = func.now()
        tenant.is_active = False
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant
