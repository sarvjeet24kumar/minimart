"""
User Schemas

Request and response schemas for user management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field

from app.common.enums import UserRole
from app.schemas.common import NormalizedModel


class UserBase(NormalizedModel):
    """Base user schema."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)



    
class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=8, max_length=128)
    tenant_id: UUID | None = None


class UserUpdate(NormalizedModel):
    """User update schema."""

    username: str | None = Field(None, min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None
    deleted_at: datetime | None = None


class UserResponse(NormalizedModel):
    """Standard user response (id on top, no sensitive status fields)."""

    id: UUID
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    tenant_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class UserAdminResponse(UserResponse):
    """Admin-level user response with status and lifecycle fields."""

    role: UserRole
    is_email_verified: bool
    is_active: bool
    deleted_at: datetime | None = None
    created_at: datetime




class ChangePasswordRequest(NormalizedModel):
    """Change password request."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
