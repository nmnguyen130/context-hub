from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status

from app.core.context import (
    RequestContext,
    UserRole,
    current_context,
    try_current_context,
)
from app.core.database import async_session
from app.core.uow import UnitOfWork

# 1. Security & Identity Context Extraction


async def get_authenticated_context() -> RequestContext:
    """Retrieve pre-authenticated RequestContext from active middleware scope."""
    ctx = try_current_context()
    if ctx is None or ctx.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return ctx


def require_roles(*roles: UserRole):
    """Ensure the authenticated user has one of the specified roles."""

    async def dependency(
        context: RequestContext = Depends(get_authenticated_context),
    ) -> RequestContext:
        if context.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return context

    return dependency


# 2. Database Scoping & Transaction Management (Unit of Work)


async def get_uow(
    context: RequestContext = Depends(get_authenticated_context),
) -> AsyncIterator[UnitOfWork]:
    """Provide a tenant-scoped Unit of Work transaction."""
    async with UnitOfWork(
        session_factory=async_session,
        context=context,
        is_admin=False,
    ) as uow:
        yield uow


async def get_public_uow() -> AsyncIterator[UnitOfWork]:
    """Provide an RLS-bypassed Unit of Work preserving request logging context."""
    async with UnitOfWork(
        session_factory=async_session,
        context=current_context(),
        is_admin=True,
    ) as uow:
        yield uow


# 3. Generic Service Factory


def get_service[T](service_class: type[T], *, public: bool = False):
    """Generic factory: returns a Depends-compatible callable for any Service(uow) class.

    Args:
        service_class: The service class to instantiate (must accept `uow` as first arg).
        public: If True, uses RLS-bypassed UoW for cross-tenant / public operations.
    """
    uow_dep = get_public_uow if public else get_uow

    async def _factory(uow: UnitOfWork = Depends(uow_dep)) -> T:
        return service_class(uow)

    return _factory
