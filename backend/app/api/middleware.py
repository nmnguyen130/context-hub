import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID

import jwt
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.database import reset_current_tenant_id, set_current_tenant_id
from app.core.enums import UserRole

# Context vars for request tracing
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_current_request_id() -> str | None:
    return _request_id_ctx.get()


def set_current_request_id(request_id: str | None) -> Token[str | None]:
    return _request_id_ctx.set(request_id)


def reset_current_request_id(token: Token[str | None]) -> None:
    _request_id_ctx.reset(token)


@dataclass
class AuthContext:
    """Resolved user identity context from JWT."""

    user_id: UUID
    tenant_id: UUID
    role: UserRole


class RequestIdMiddleware:
    """ASGI Middleware to trace requests with unique Correlation IDs."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        scope.setdefault("state", {})
        headers = dict(scope.get("headers", []))

        # Resolve or generate X-Request-ID
        req_id_header = headers.get(b"x-request-id")
        request_id = req_id_header.decode() if req_id_header else uuid.uuid4().hex
        scope["state"]["request_id"] = request_id

        # Inject to context var for log tracing
        token = set_current_request_id(request_id)

        # Inject X-Request-ID into response headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers_list = message.get("headers", [])
                headers_list.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers_list
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_current_request_id(token)


class TenantAuthMiddleware:
    """ASGI Middleware to resolve tenant context and enforce JWT security."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        scope.setdefault("state", {})
        headers = dict(scope.get("headers", []))

        # 1. Resolve Auth identity
        identity = None
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
                    identity = AuthContext(
                        user_id=UUID(payload["sub"]),
                        tenant_id=UUID(payload["tenant_id"]),
                        role=UserRole(payload.get("role", UserRole.MEMBER)),
                    )
                    scope["state"]["identity"] = identity
            except (ValueError, KeyError, jwt.PyJWTError):
                response = JSONResponse(
                    status_code=401,
                    content={"detail": "Could not validate credentials"},
                )
                await response(scope, receive, send)
                return

        # 2. Enforce Tenant safety (only trust JWT, ignore headers for anonymous requests)
        tenant_id = None
        if identity:
            tenant_id = identity.tenant_id

            # If client provides a tenant header, ensure it matches JWT
            if tenant_header := headers.get(b"x-tenant-id"):
                try:
                    provided_tenant_id = UUID(tenant_header.decode())
                    if identity.tenant_id != provided_tenant_id:
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

        # 3. Bind context and forward request
        token = set_current_tenant_id(tenant_id)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_current_tenant_id(token)
