# app/core/context.py
from __future__ import annotations
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, asdict
from typing import Iterator
from app.core.enums import UserRole

@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    correlation_id: str
    tenant_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    role: UserRole | None = None
    is_platform_admin: bool = False
    ip_address: str | None = None
    user_agent: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tenant_id"] = str(self.tenant_id) if self.tenant_id else None
        d["actor_id"] = str(self.actor_id) if self.actor_id else None
        d["role"] = self.role.value if self.role else None
        return d

_ctx_var: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)

def current_context() -> RequestContext:
    ctx = _ctx_var.get()
    if ctx is None:
        raise RuntimeError("RequestContext accessed outside a bound scope")
    return ctx

def current_context_or_none() -> RequestContext | None:
    return _ctx_var.get()

@contextmanager
def bind_context(ctx: RequestContext) -> Iterator[RequestContext]:
    """Bind a context for the current scope. Safe to call from middleware,
    background workers, or tests. Auto-resets on exit, including on exception."""
    token: Token = _ctx_var.set(ctx)
    try:
        yield ctx
    finally:
        _ctx_var.reset(token)
