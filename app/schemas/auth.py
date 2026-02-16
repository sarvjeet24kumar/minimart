"""
Authentication Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.constants import (
    MAX_LENGTH_NAME,
    MIN_LENGTH_NAME,
    MAX_LENGTH_USERNAME,
    MIN_LENGTH_USERNAME,
    MAX_LENGTH_PASSWORD_RAW,
    MIN_LENGTH_PASSWORD,
    MIN_LENGTH_PASSWORD_LOGIN,
    MAX_LENGTH_TOKEN,
    MIN_LENGTH_TOKEN,
    OTP_LENGTH,
    REGEX_USERNAME,
    MSG_OTP_SENT,
)
from app.schemas.common import NormalizedModel


class LoginRequest(NormalizedModel):
    """Login request payload."""

    email: EmailStr
    password: str = Field(..., min_length=MIN_LENGTH_PASSWORD_LOGIN, max_length=MAX_LENGTH_PASSWORD_RAW)


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
    otp: str = Field(..., min_length=OTP_LENGTH, max_length=OTP_LENGTH)


class ResendOtpRequest(NormalizedModel):
    email: EmailStr


class OTPResponse(BaseModel):
    """OTP sent response."""

    message: str = MSG_OTP_SENT
    expires_in: int = Field(..., description="OTP expiry in seconds")

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(NormalizedModel):
    """Password reset request."""

    email: EmailStr


class PasswordResetConfirm(NormalizedModel):
    """Password reset confirmation."""

    token: str = Field(..., min_length=MIN_LENGTH_TOKEN, max_length=MAX_LENGTH_TOKEN)
    new_password: str = Field(..., min_length=MIN_LENGTH_PASSWORD, max_length=MAX_LENGTH_PASSWORD_RAW)
    confirm_password: str = Field(..., min_length=MIN_LENGTH_PASSWORD, max_length=MAX_LENGTH_PASSWORD_RAW)


class SignupRequest(NormalizedModel):
    """User signup request."""

    email: EmailStr
    username: str = Field(..., min_length=MIN_LENGTH_USERNAME, max_length=MAX_LENGTH_USERNAME, pattern=REGEX_USERNAME)
    first_name: str = Field(..., min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)
    last_name: str = Field(..., min_length=MIN_LENGTH_NAME, max_length=MAX_LENGTH_NAME)
    password: str = Field(..., min_length=MIN_LENGTH_PASSWORD, max_length=MAX_LENGTH_PASSWORD_RAW)


class LogoutRequest(NormalizedModel):
    """Logout request."""

    refresh_token: str
