import re
from typing import Annotated

from fastapi import Request, Depends
from app.exceptions import RateLimitException
from app.services.redis_service import RedisService

class RateLimit:
    """
    Custom Redis-based rate limiting dependency.
    """
    
    def __init__(self, limit_str: str, scope: str = "default"):
        self.limit_str = limit_str
        self.scope = scope
        self.limit, self.window = self._parse_limit(limit_str)

    def _parse_limit(self, limit_str: str) -> tuple[int, int]:
        """
        Parses limit string like "5/minute" or "10/hour" into (count, seconds).
        """
        match = re.match(r"(\d+)\/(second|minute|hour|day)", limit_str.lower())
        if not match:
            # Default to 10/minute if parsing fails
            return 10, 60
        
        count = int(match.group(1))
        unit = match.group(2)
        
        seconds_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        return count, seconds_map.get(unit, 60)

    async def __call__(self, request: Request):

        ip = request.client.host if request.client else "unknown"
        

        route = request.scope.get("route")
        endpoint_id = route.path if route and hasattr(route, "path") else request.url.path
        

        key = f"rl:{self.scope}:{endpoint_id}:{ip}"
        
        redis = await RedisService.get_client()
        
        count = await redis.incr(key)
        
        if count == 1:
            await redis.expire(key, self.window)
        
        if count > self.limit:
            raise RateLimitException(
                message="Rate limit exceeded"
            
            )
