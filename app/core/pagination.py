"""
Pagination Utilities
"""

from fastapi import Query
from app.common.constants import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
)


class PaginationParams:
    """Dependency for normalized pagination parameters."""

    def __init__(
        self,
        page: int = Query(DEFAULT_PAGE, ge=DEFAULT_PAGE),
        size: int = Query(
            DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE
        ),
    ):
        self.page = page
        self.size = size
        self.skip = (self.page - 1) * self.size
