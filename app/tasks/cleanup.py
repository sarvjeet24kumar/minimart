"""
Cleanup Tasks

Periodic maintenance tasks for database cleanup.
"""

import asyncio

from app.core.celery import celery_app
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.services.invitation import InvitationMaintenanceService

logger = get_logger(__name__)

@celery_app.task(name="app.tasks.expire_invites")
def expire_invites():
    """
    Background task to mark stale invitations as expired.
    """
    async def run_cleanup():
        async with AsyncSessionLocal() as db:
            service = InvitationMaintenanceService(db)
            try:
                count = await service.expire_stale_invites()
                if count > 0:
                    logger.info("Background cleanup: Expired %d invitations.", count)
                return count
            except Exception as e:
                logger.error("Background cleanup failed: %s", str(e))
                raise

    return asyncio.run(run_cleanup())
