"""
Celery Configuration

Sets up the Celery application and defines the background task schedule.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "minimart",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.cleanup"],
)

# Define the Beat schedule
celery_app.conf.beat_schedule = {
    "expire-invitations-every-hour": {
        "task": "app.tasks.expire_invites",
        "schedule": crontab(minute=0),  # Run every hour
    },
}
