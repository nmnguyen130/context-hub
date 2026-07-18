from __future__ import annotations

import uuid
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"

    @property
    def priority(self) -> int:
        return {
            UserRole.SUPER_ADMIN: 5,
            UserRole.OWNER: 4,
            UserRole.ADMIN: 3,
            UserRole.MEMBER: 2,
            UserRole.VIEWER: 1,
        }[self]

    def has_higher_privilege_than(self, other: "UserRole") -> bool:
        """Check if this role has strictly higher authority than the other."""
        if self == UserRole.SUPER_ADMIN:
            return True
        return self.priority > other.priority


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    trace_id: str
    tenant_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    role: UserRole | None = None
    plan: str = "free"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "role": self.role,
            "plan": self.plan,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, str | None]) -> RequestContext:
        return cls(
            request_id=data.get("request_id") or "",
            trace_id=data.get("trace_id") or "",
            tenant_id=uuid.UUID(data["tenant_id"]) if data.get("tenant_id") else None,
            user_id=uuid.UUID(data["user_id"]) if data.get("user_id") else None,
            role=UserRole(data["role"]) if data.get("role") else None,
            plan=data.get("plan") or "free",
        )


_context: ContextVar[RequestContext | None] = ContextVar(
    "request_context", default=None
)


def current_context() -> RequestContext:
    ctx = _context.get()
    if ctx is None:
        raise RuntimeError("RequestContext accessed outside a bound scope")
    return ctx


def try_current_context() -> RequestContext | None:
    return _context.get()


@contextmanager
def bind_context(ctx: RequestContext):
    """Scoped context manager ensuring clean ContextVar binding and restoration."""
    token = _context.set(ctx)
    try:
        yield ctx
    finally:
        _context.reset(token)
