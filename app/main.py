"""
MiniMart FastAPI Application
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import  FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.database import close_db, init_db
from app.exceptions.handlers import setup_exception_handlers
from app.middleware.logging import LoggingMiddleware
from app.services.redis_service import RedisService
from app.websocket.endpoints import router as ws_router

# Initialize logging as early as possible
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""

    # Ensure Redis is connected
    await RedisService.get_client() 
    await RedisService.get_token_client()
     
    if settings.is_development:
        await init_db()
    
    yield
    
    # Shutdown
    print("Shutting down MiniMart API...")
    await RedisService.close()
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-tenant shopping list application",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)



# Setup exception handlers
setup_exception_handlers(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
app.add_middleware(LoggingMiddleware)

# Include routes
app.include_router(health_router, prefix="/health")
app.include_router(api_router)
app.include_router(ws_router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )
