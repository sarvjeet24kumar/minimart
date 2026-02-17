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
    Allows applying limits without adding 'request: Request' to the endpoint signature.
    
    Usage:
        @router.get("/", dependencies=[Depends(RateLimit("5/minute", scope="auth"))])
    """
    def __init__(self, limit_str: str, scope: str = "default"):
        self.limit_str = limit_str
        self.scope = scope

    async def __call__(self, request: Request):
        # We manually trigger the limiter's check logic
        # This bypasses the decorator's requirement for the argument in the signature
        
        # Parse the limit string into RateLimitItem objects
        # parse_many returns a list of items
        items = parse_many(self.limit_str)
        if not items:
            return

        # Get the identifier for the request (IP address)
        ip = get_remote_address(request)
        
        # We include the route path to ensure endpoints don't block each other.
        # We try to use the path template (e.g. /users/{user_id}) if available.
        route = request.scope.get("route")
        endpoint_id = route.path if route and hasattr(route, "path") else request.url.path
        
        key = f"{self.scope}:{endpoint_id}:{ip}"

        # Check each limit item using the internal limiter object
        for item in items:
            if not limiter._limiter.hit(item, key):
                 # Raise RateLimitExceeded using a mock Limit object to satisfy
                 # version-specific constructor requirements (needs .error_message and .limit)
                 raise RateLimitExceeded(MockLimit(item))
