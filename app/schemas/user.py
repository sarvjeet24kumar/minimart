"""
User Schemas

Request and response schemas for user management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field

from app.common.enums import UserRole
from app.common.constants import (
    MAX_LENGTH_NAME,
    MIN_LENGTH_NAME,
    MAX_LENGTH_USERNAME,
    MIN_LENGTH_USERNAME,
    MAX_LENGTH_PASSWORD_RAW,
    MIN_LENGTH_PASSWORD,
    REGEX_USERNAME,
)
from app.schemas.common import NormalizedModel


class UserBase(NormalizedModel):
    """Base user schema."""

    email: EmailStr
    username: str = Field(
        ...,
        min_length=MIN_LENGTH_USERNAME,
        max_length=MAX_LENGTH_USERNAME,
        pattern=REGEX_USERNAME,
    )
    first_name: str = Field(..., min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)
    last_name: str = Field(..., min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(
        ..., min_length=MIN_LENGTH_PASSWORD, max_length=MAX_LENGTH_PASSWORD_RAW
    )
    tenant_id: UUID | None = None


class UserUpdate(NormalizedModel):
    """User update schema."""

    username: str | None = Field(
        None,
        min_length=MIN_LENGTH_USERNAME,
        max_length=MAX_LENGTH_USERNAME,
        pattern=REGEX_USERNAME,
    )
    first_name: str | None = Field(
        None, min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME
    )
    last_name: str | None = Field(
        None, min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME
    )
    is_active: bool | None = None
    deleted_at: datetime | None = None


class UserResponse(NormalizedModel):
    """Standard user response (id on top, no sensitive status fields)."""

    id: UUID
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class UserAdminResponse(UserResponse):
    """Admin-level user response with status and lifecycle fields."""

    is_email_verified: bool
    is_active: bool
    tenant_id: UUID | None = None
    deleted_at: datetime | None = None
    created_at: datetime


class ChangePasswordRequest(NormalizedModel):
    """Change password request."""

    current_password: str = Field(..., min_length=MIN_LENGTH_PASSWORD)
    new_password: str = Field(
        ..., min_length=MIN_LENGTH_PASSWORD, max_length=MAX_LENGTH_PASSWORD_RAW
    )
