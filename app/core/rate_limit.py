from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from limits import parse_many
from app.core.config import settings

# Initialize limiter with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",
)

class MockLimit:
    """
    Mock class to satisfy RateLimitExceeded constructor requirements
    in diverse slowapi versions.
    """
    def __init__(self, item, error_message=None):
        self.limit = item
        self.error_message = error_message

class RateLimit:
    """
    Dependency-based rate limiting with granular endpoint isolation.

    """
    def __init__(self, limit_str: str, scope: str = "default"):
        self.limit_str = limit_str
        self.scope = scope

    async def __call__(self, request: Request):
        items = parse_many(self.limit_str)
        if not items:
            return

        ip = get_remote_address(request)
        
        route = request.scope.get("route")
        endpoint_id = route.path if route and hasattr(route, "path") else request.url.path
        
        key = f"{self.scope}:{endpoint_id}:{ip}"

        for item in items:
            if not limiter._limiter.hit(item, key):
                raise RateLimitExceeded(MockLimit(item))
