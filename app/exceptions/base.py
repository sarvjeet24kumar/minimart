"""
Base Exception
"""

from typing import Any

from fastapi import HTTPException


class MiniMartException(HTTPException):
    """Base exception for MiniMart application."""

    def __init__(
        self,
        status_code: int,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.details = details
        super().__init__(
            status_code=status_code,
            detail={
                "message": message,
                "details": details,
            },
            headers=headers,
        )
