import logging
import os
import re
import sys
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from typing import Any

# Context variables for tenant and request tracking
tenant_id_context: ContextVar[str] = ContextVar("tenant_id", default="N/A")
request_id_context: ContextVar[str] = ContextVar("request_id", default="N/A")

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "minimart.log")

# Unified format with explicit labels for request and tenant IDs
LOG_FORMAT = "%(asctime)s %(levelname)-8s request_id %(request_id)s tenant_id %(tenant_id)s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class TenantFilter(logging.Filter):
    """Filter to add tenant_id and request_id to log records from ContextVars."""
    def filter(self, record):
        record.tenant_id = tenant_id_context.get()
        record.request_id = request_id_context.get()
        return True


import logging.config

def setup_logging(level: str = "INFO") -> None:
    """Configure simplified logging with centralized dictConfig."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
            },
        },
        "filters": {
            "tenant_filter": {
                "()": TenantFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
                "level": numeric_level,
                "filters": ["tenant_filter"],
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": LOG_FILE,
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "level": numeric_level,
                "filters": ["tenant_filter"],
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": numeric_level,
            },
            "uvicorn": {
                "handlers": [],
                "propagate": True,
            },
            "uvicorn.error": {
                "handlers": [],
                "propagate": True,
            },
            "uvicorn.access": {
                "handlers": [],
                "propagate": True,
                "level": "WARNING",
            },
            "sqlalchemy.engine": {
                "handlers": [],
                "level": "WARNING",
                "propagate": True,
            },
            "aiosqlite": {
                "handlers": [],
                "level": "WARNING",
                "propagate": True,
            },
        },
    }

    # Clear root handlers first before applying dictConfig to be extra safe
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    logging.config.dictConfig(logging_config)
    
    logging.getLogger(__name__).info(f"Logging system unified via dictConfig. Level: {level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)
