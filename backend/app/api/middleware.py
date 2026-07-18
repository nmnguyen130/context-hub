import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import RequestContext, UserRole, bind_context
from app.utils.security import decode_token


class RequestContextMiddleware:
    """ASGI middleware enforcing trace tracking boundary, JWT authentication, and context initialization."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))

        # 1. Extract Tracing Correlation IDs
        req_id = headers.get(b"x-request-id", b"").decode("utf-8") or str(uuid.uuid4())
        trace_id = headers.get(b"x-trace-id", b"").decode("utf-8") or req_id

        # 2. Parse Authentication & Context claims
        tenant_id, user_id, role, plan = None, None, None, "free"
        auth = headers.get(b"authorization", b"").decode("utf-8")
        if auth.startswith("Bearer "):
            try:
                jwt_payload = decode_token(auth.split(" ")[1], expected_type="access")
                tenant_id = uuid.UUID(jwt_payload["tenant_id"]) if jwt_payload.get("tenant_id") else None
                user_id = uuid.UUID(jwt_payload["sub"]) if jwt_payload.get("sub") else None
                role = UserRole(jwt_payload["role"]) if jwt_payload.get("role") else None
                plan = jwt_payload.get("plan", "free")
            except Exception:
                pass

        ctx = RequestContext(
            request_id=req_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            plan=plan,
        )

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-request-id", req_id.encode("utf-8")))
                headers_list.append((b"x-trace-id", trace_id.encode("utf-8")))
                message["headers"] = headers_list
            await send(message)

        with bind_context(ctx):
            await self.app(scope, receive, send_wrapper)
