"""
Notification Endpoints
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import PaginationParams, get_current_verified_user
from app.core.rate_limit import RateLimit
from app.db.session import get_db
from app.exceptions import NotFoundException
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(dependencies=[Depends(RateLimit(settings.RATE_LIMIT_DEFAULT, scope="notifications"))])


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    is_read: bool | None = Query(None, description="Filter by read/unread status"),
):
    """
    Get notifications for the current user.
    """
    notification_service = NotificationService(db)
    return await notification_service.get_user_notifications(
        current_user.id,
        pagination,
        is_read=is_read,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_notification_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Mark a notification as read.
    """
    notification_service = NotificationService(db)
    return await notification_service.mark_as_read(notification_id, current_user.id)


@router.patch(
    "/read-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Mark all unread notifications as read.
    """
    notification_service = NotificationService(db)
    return await notification_service.mark_all_as_read(current_user.id)
