import jwt
from uuid import UUID
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.tenant_context import set_current_tenant_id, reset_current_tenant_id

class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts all HTTP requests and inspects headers or JWT tokens
    to resolve the request's active tenant. The resolved tenant ID is bound to 
    the request-scoped contextvar to enforce logical data isolation.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_id = None
        
        # 1. Attempt extraction from custom test/service-to-service header
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            try:
                tenant_id = UUID(tenant_header)
            except ValueError:
                pass # Invalid UUID format
                
        # 2. Attempt extraction from JWT Authorization header
        if not tenant_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Robust extraction of the Bearer token
                parts = auth_header.split(" ", 1)
                token = parts[1] if len(parts) > 1 else auth_header[7:]
                try:
                    payload = jwt.decode(
                        token,
                        settings.JWT_SECRET,
                        algorithms=[settings.JWT_ALGORITHM]
                    )
                    tenant_id_str = payload.get("tenant_id")
                    if tenant_id_str:
                        tenant_id = UUID(tenant_id_str)
                except (jwt.PyJWTError, ValueError):
                    # We do not block here; path-specific authentication dependencies
                    # (like oauth2 schemes) will raise 401 Unauthorized if required.
                    pass

        # Set the thread-safe context variable
        context_token = set_current_tenant_id(tenant_id)
        try:
            response = await call_next(request)
            return response
        finally:
            # Always reset context variable to prevent cross-request leakage
            reset_current_tenant_id(context_token)
