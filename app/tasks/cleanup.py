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
        from app.db.database import engine
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
            finally:
                await engine.dispose()

    return asyncio.run(run_cleanup())

@celery_app.task(name="app.tasks.cleanup_maintenance")
def cleanup_maintenance():
    """
    Periodic task to run all maintenance cleanup routines.
    """
    from app.services.maintenance_service import MaintenanceService
    
    async def run_maintenance():
        from app.db.database import engine
        async with AsyncSessionLocal() as db:
            service = MaintenanceService(db)
            try:
                # 1. Clear unverified users
                unverified_count = await service.hard_delete_unverified_users()
                
                # 2. Erase data for old soft-deleted users
                user_data_count = await service.erase_deleted_user_data()
                
                # 3. Clear expired tenants
                tenant_count = await service.hard_delete_expired_tenants()
                
                logger.info(
                    "Maintenance completed: %d unverified users deleted, %d users data erased, %d tenants deleted.",
                    unverified_count, user_data_count, tenant_count
                )
            except Exception as e:
                logger.error("Maintenance task failed: %s", str(e))
                raise
            finally:
                await engine.dispose()

    return asyncio.run(run_maintenance())
