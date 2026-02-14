"""
Authentication Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import NormalizedModel


class LoginRequest(NormalizedModel):
    """Login request payload."""

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class LoginResponse(BaseModel):
    """Login response with tokens."""

    access_token: str
    refresh_token: str

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(NormalizedModel):
    """Refresh token request."""

    refresh_token: str


class VerifyEmailRequest(NormalizedModel):
    """Email verification request with OTP."""

    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(NormalizedModel):
    email: EmailStr


class OTPResponse(BaseModel):
    """OTP sent response."""

    message: str = "OTP sent successfully"
    expires_in: int = Field(..., description="OTP expiry in seconds")

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(NormalizedModel):
    """Password reset request."""

    email: EmailStr


class PasswordResetConfirm(NormalizedModel):
    """Password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class SignupRequest(NormalizedModel):
    """User signup request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class LogoutRequest(NormalizedModel):
    """Logout request."""

    refresh_token: str
