"""
Tenant Schemas

Request and response schemas for tenant management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.common import NormalizedModel


class TenantCreate(NormalizedModel):
    """Tenant creation schema (name and slug only)."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class TenantUpdate(NormalizedModel):
    """Tenant update schema."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    is_active: bool | None = None
    deleted_at: datetime | None = None


class TenantResponse(NormalizedModel):
    """Tenant response schema."""

    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)