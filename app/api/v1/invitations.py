"""
Invitation Endpoints

"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.config import settings
from app.core.dependencies import PaginationParams, get_current_verified_user
from app.core.rate_limit import RateLimit
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.invitation import (
    InvitationRespondRequest,
    InvitationResponse,
    InviteRequest,
    InviteResponse,
)
from app.services.invitation import (
    InvitationActionService,
    InvitationManagementService,
)

router = APIRouter(dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API))])
list_router = APIRouter(dependencies=[Depends(RateLimit(settings.RATE_LIMIT_API, scope="invitations"))])


@router.post(
    "/respond",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def respond_to_invitation(
    data: InvitationRespondRequest,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Accept or reject a shopping list invitation.
    """
    action_service = InvitationActionService(db)
    return await action_service.respond_to_invitation(data.token, data.action, current_user)


@router.delete(
    "/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_invitation(
    invite_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Cancel a pending invitation.
    """
    management_service = InvitationManagementService(db)
    await management_service.cancel_invitation(invite_id, current_user)


@router.post(
    "/{invite_id}/resend",
    response_model=InviteResponse,
    status_code=status.HTTP_200_OK,
)
async def resend_invitation(
    invite_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    """
    Resend a pending invitation.

    """
    management_service = InvitationManagementService(db)
    return await management_service.resend_invitation(
        invite_id, current_user, background_tasks
    )


@list_router.get(
    "/invites",
    response_model=PaginatedResponse[InvitationResponse],
    status_code=status.HTTP_200_OK,
)
async def get_my_invites(
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status: PENDING, ACCEPTED, REJECTED, CANCELLED, EXPIRED",
    ),
):
    """
    Get all invitations for the current user across all lists.
    """
    management_service = InvitationManagementService(db)
    return await management_service.get_my_invites(
        current_user,
        pagination=pagination,
        status_filter=status_filter,
    )


@list_router.post(
    "/{list_id}/invite",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    list_id: UUID,
    data: InviteRequest,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    """
    Invite a user to join the shopping list.
    """
    management_service = InvitationManagementService(db)
    return await management_service.send_invitation(
        list_id, data.user_id, current_user, background_tasks
    )


@list_router.get(
    "/{list_id}/invites",
    response_model=PaginatedResponse[InvitationResponse],
    status_code=status.HTTP_200_OK,
)
async def get_list_invites(
    list_id: UUID,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status: PENDING, ACCEPTED, REJECTED, CANCELLED, EXPIRED",
    ),
):
    """
    Get all invitations for a specific shopping list.
    """
    management_service = InvitationManagementService(db)
    return await management_service.get_list_invites(
        list_id,
        current_user,
        pagination=pagination,
        status_filter=status_filter,
    )
