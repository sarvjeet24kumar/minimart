"""
Tenant Schemas

Request and response schemas for tenant management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.common import NormalizedModel


from app.common.constants import (
    MAX_LENGTH_NAME,
    MIN_LENGTH_NAME,
    MAX_LENGTH_SLUG,
    MIN_LENGTH_SLUG,
    REGEX_SLUG,
)


class TenantCreate(NormalizedModel):
    """Tenant creation schema (name and slug only)."""

    name: str = Field(..., min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)
    slug: str = Field(
        ..., min_length=MIN_LENGTH_SLUG, max_length=MAX_LENGTH_SLUG, pattern=REGEX_SLUG
    )


class TenantUpdate(NormalizedModel):
    """Tenant update schema."""

    name: str | None = Field(
        None, min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME
    )
    slug: str | None = Field(
        None, min_length=MIN_LENGTH_SLUG, max_length=MAX_LENGTH_SLUG, pattern=REGEX_SLUG
    )
    is_active: bool | None = None
    deleted_at: datetime | None = None


class TenantResponse(NormalizedModel):
    """Base tenant response schema."""

    id: UUID
    name: str
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantDetailResponse(TenantResponse):
    """Detailed tenant response with status fields and counts."""

    is_active: bool
    updated_at: datetime
    deleted_at: datetime | None = None
    total_users: int = 0
    total_lists: int = 0
    total_items: int = 0
