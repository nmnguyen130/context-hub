import contextvars
from typing import Optional
from uuid import UUID

# Thread-safe ContextVar to hold the active tenant ID for SQL operations
_tenant_id_context: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "tenant_id", default=None
)


def get_current_tenant_id() -> Optional[UUID]:
    """Retrieve the current tenant ID from request context."""
    return _tenant_id_context.get()


def set_current_tenant_id(
    tenant_id: Optional[UUID],
) -> contextvars.Token[Optional[UUID]]:
    """Set the current tenant ID in request context."""
    return _tenant_id_context.set(tenant_id)


def reset_current_tenant_id(token: contextvars.Token[Optional[UUID]]) -> None:
    """Reset the tenant context to its previous state."""
    _tenant_id_context.reset(token)
