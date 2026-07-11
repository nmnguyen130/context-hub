# app/api/middleware.py
import uuid
import jwt
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.context import RequestContext, bind_context
from app.core.enums import UserRole

class RequestContextMiddleware:
    """ASGI Middleware to trace requests and resolve tenant context using a unified RequestContext."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        scope.setdefault("state", {})
        headers = dict(scope.get("headers", []))

        # 1. Resolve or generate Request and Correlation IDs
        req_id_header = headers.get(b"x-request-id")
        request_id = req_id_header.decode() if req_id_header else uuid.uuid4().hex
        
        corr_id_header = headers.get(b"x-correlation-id")
        correlation_id = corr_id_header.decode() if corr_id_header else request_id

        scope["state"]["request_id"] = request_id

        # 2. Resolve Auth identity (JWT decode, spoofing checks)
        tenant_id = None
        actor_id = None
        role = None
        is_platform_admin = False

        auth_header = headers.get(b"authorization")
        if auth_header:
            try:
                scheme, token = auth_header.decode().split(" ", 1)
                if scheme.lower() == "bearer":
                    payload = jwt.decode(
                        token,
                        settings.JWT_SECRET,
                        algorithms=[settings.JWT_ALGORITHM],
                    )
                    if payload.get("type") != "access":
                        response = JSONResponse(
                            status_code=401,
                            content={"detail": "Invalid token type"},
                        )
                        await response(scope, receive, send)
                        return

                    actor_id = uuid.UUID(payload["sub"])
                    tenant_id = uuid.UUID(payload["tenant_id"])
                    role = UserRole(payload.get("role", UserRole.MEMBER.value))
                    is_platform_admin = (role == UserRole.ADMIN)

                    # Store identity on scope for compatibility
                    from dataclasses import dataclass
                    @dataclass
                    class CompatibilityIdentity:
                        user_id: uuid.UUID
                        tenant_id: uuid.UUID
                        role: UserRole

                    scope["state"]["identity"] = CompatibilityIdentity(
                        user_id=actor_id,
                        tenant_id=tenant_id,
                        role=role
                    )

            except (ValueError, KeyError, jwt.PyJWTError):
                response = JSONResponse(
                    status_code=401,
                    content={"detail": "Could not validate credentials"},
                )
                await response(scope, receive, send)
                return

        # 3. If client provides a tenant header, ensure it matches JWT
        if tenant_id and (tenant_header := headers.get(b"x-tenant-id")):
            try:
                provided_tenant_id = uuid.UUID(tenant_header.decode())
                if tenant_id != provided_tenant_id:
                    response = JSONResponse(
                        status_code=403,
                        content={"detail": "Tenant context mismatch"},
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Tenant ID format"},
                )
                await response(scope, receive, send)
                return

        # 4. Construct unified RequestContext
        client_host = scope.get("client", (None,))[0]
        user_agent = headers.get(b"user-agent", b"").decode() or None

        ctx = RequestContext(
            request_id=request_id,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            role=role,
            is_platform_admin=is_platform_admin,
            ip_address=client_host,
            user_agent=user_agent,
        )

        # 5. Bind context and forward request
        with bind_context(ctx):
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers_list = message.get("headers", [])
                    headers_list.append((b"x-request-id", request_id.encode()))
                    headers_list.append((b"x-correlation-id", correlation_id.encode()))
                    message["headers"] = headers_list
                await send(message)

            await self.app(scope, receive, send_wrapper)
