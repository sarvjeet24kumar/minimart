"""
Exception Handlers

Unified error response format for all exceptions.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded

from app.exceptions.base import MiniMartException


async def minimart_exception_handler(request: Request, exc: MiniMartException):
    """Handler for all MiniMart-specific exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.detail.get("message", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail),
                "details": exc.detail.get("details", {}) if isinstance(exc.detail, dict) else {},
            },
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for Pydantic validation errors."""
    formatted_errors = {}
    for error in exc.errors():
        field = error["loc"][-1] if error["loc"] else "general"
        formatted_errors.setdefault(str(field), []).append(error["msg"])

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "message": "Invalid input",
                "details": formatted_errors,
            },
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler for generic HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": str(exc.detail),
                "details": {},
            },
        },
    )


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "message": "Too many requests. Please try again later.",
                "details": {"limit": str(exc.detail)},
            },
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers to the FastAPI app."""
    app.add_exception_handler(MiniMartException, minimart_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
