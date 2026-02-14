"""
Health Check Endpoints
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.redis_service import RedisService

router = APIRouter()

@router.get("", tags=["Health"])
async def health_check():
    """Basic liveness check."""
    return {"success": True, "data": {"status": "healthy", "app": settings.APP_NAME}}


@router.get("/ready", tags=["Health"])
async def readiness_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Readiness check including database and Redis connectivity.
    """
    errors = []
    
    # Check database
    try:
        await db.execute(select(1))
    except Exception as e:
        errors.append(f"Database: {str(e)}")
    
    # Check Redis
    try:
        client = await RedisService.get_client()
        await client.ping()
    except Exception as e:
        errors.append(f"Redis: {str(e)}")
    
    if errors:
        return JSONResponse(
            status_code=503,
            content={
                "success": False, 
                "error": {
                    "code": "UNHEALTHY", 
                    "message": "Service unhealthy", 
                    "details": {"errors": errors}
                }
            },
        )
    
    return {"success": True, "data": {"status": "ready"}}
