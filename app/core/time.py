"""
Time Utilities
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def get_now() -> datetime:
    """Get current time in configured timezone."""
    return datetime.now(ZoneInfo(settings.TIMEZONE))

