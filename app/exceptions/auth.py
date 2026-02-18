"""
Auth exceptions
"""

from typing import Any

from fastapi import status

from app.exceptions.base import MiniMartException


class UnauthorizedException(MiniMartException):
    """401 Unauthorized - Missing or invalid credentials."""

    def __init__(
        self,
        message: str = "Invalid credentials",
        details: Any | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            details=details,
        )


class ForbiddenException(MiniMartException):
    """403 Forbidden - Insufficient permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Any | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            details=details,
        )


class EmailNotVerifiedException(MiniMartException):
    """403 Forbidden - Email not verified."""

    def __init__(
        self,
        message: str = "Email not verified",
        details: Any | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            details=details,
        )


class InvitationExpiredException(MiniMartException):
    """400 Bad Request - Invitation has expired."""

    def __init__(
        self,
        message: str = "Invitation has expired",
        details: Any | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            details=details,
        )


class InvitationAlreadyUsedException(MiniMartException):
    """400 Bad Request - Invitation has already been used."""

    def __init__(
        self,
        message: str = "Invitation has already been used",
        details: Any | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            details=details,
        )
