import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger, tenant_id_context, request_id_context
from app.core.security import decode_token

logger = get_logger("app.middleware.logging")

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses with Tenant ID context."""

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        return await super().__call__(scope, receive, send)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        request_id = request.headers.get("Request-ID", str(uuid.uuid4())[:8])
        
        tenant_id = "N/A"
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_token(token)
                tenant_id = payload.get("tenant_id", "N/A")
            except Exception:
                pass
        
        token_ctx = tenant_id_context.set(tenant_id)
        request_ctx = request_id_context.set(request_id)
        
        method = request.method
        
        path = request.url.path
        
        logger.info(f"Request: {method} {path}")

        try:
            response = await call_next(request)
            
            process_time = time.time() - start_time
            status_code = response.status_code
            

            logger.info(
                f"Response: {method} {path} {status_code} ({process_time:.3f}s)"
            )
            
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Failed: {method} {path} Error: {str(e)} ({process_time:.3f}s)",
                exc_info=True
            )
            raise
        finally:
            tenant_id_context.reset(token_ctx)
            request_id_context.reset(request_ctx)
