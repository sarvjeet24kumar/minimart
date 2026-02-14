"""
Security Utilities

Password hashing, JWT token operations, and OTP generation.
"""

import secrets
import string
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings
from app.core.time import get_now

ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(
    user_id: UUID,
    tenant_id: UUID | None,
    role: str,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.
    """
    if expires_delta:
        expire = get_now() + expires_delta
    else:
        expire = get_now() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "email": email,
        "exp": expire,
        "iat": get_now(),
        "jti": str(uuid4()),
        "type": "access",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    tenant_id: UUID | None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.
    """
    if expires_delta:
        expire = get_now() + expires_delta
    else:
        expire = get_now() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "exp": expire,
        "iat": get_now(),
        "jti": str(uuid4()),
        "type": "refresh",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return payload


def generate_otp(length: int | None = None) -> str:
    """
    Generate a random OTP code.

    """
    if length is None:
        length = settings.OTP_LENGTH
    return "".join(secrets.choice(string.digits) for _ in range(length))


def create_invitation_token(
    list_id: UUID,
    email: str,
    tenant_id: UUID | None,
    inviter_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT invitation token for list invites.

    """
    if expires_delta:
        expire = get_now() + expires_delta
    else:
        expire = get_now() + timedelta(
            hours=settings.INVITATION_TOKEN_EXPIRE_HOURS
        )

    payload = {
        "type": "list_invite",
        "list_id": str(list_id),
        "email": email,
        "tenant_id": str(tenant_id),
        "inviter_id": str(inviter_id),
        "exp": expire,
        "iat": get_now(),
        "jti": str(uuid4()),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_invitation_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an invitation token.

    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    
    if payload.get("type") != "list_invite":
        raise JWTError("Invalid token type")
    
    return payload


def create_password_reset_token(
    user_id: UUID,
    tenant_id: UUID | None,
) -> str:
    """
    Create a JWT password reset token.

    """
    expire = get_now() + timedelta(minutes=15)

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "type": "password_reset",
        "exp": expire,
        "iat": get_now(),
        "jti": str(uuid4()),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_password_reset_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a password reset token.

    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    if payload.get("type") != "password_reset":
        raise JWTError("Invalid token type")

    return payload
