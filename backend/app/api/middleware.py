import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import RequestContext, bind_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing trace tracking boundary and context initialization."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        trace_id = request.headers.get("X-Trace-ID") or req_id

        ctx = RequestContext(
            request_id=req_id,
            trace_id=trace_id,
        )

        with bind_context(ctx):
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Trace-ID"] = trace_id
            return response
