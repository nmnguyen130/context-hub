import uuid
from dataclasses import replace
from typing import AsyncIterator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.context import RequestContext, UserRole, bind_context, current_context
from app.core.database import async_session
from app.core.uow import UnitOfWork
from app.utils.security import decode_token

security = HTTPBearer()


async def get_authenticated_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AsyncIterator[RequestContext]:
    """Authenticates credentials, decodes JWT claims, and binds mutated RequestContext."""
    try:
        payload = decode_token(credentials.credentials, expected_type="access")

        tenant_id = uuid.UUID(t) if (t := payload.get("tenant_id")) else None
        user_id = uuid.UUID(s) if (s := payload.get("sub")) else None
        role = UserRole(r) if (r := payload.get("role")) else None

    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    ctx = current_context()
    updated_ctx = replace(ctx, tenant_id=tenant_id, user_id=user_id, role=role)

    with bind_context(updated_ctx):
        yield updated_ctx


async def get_uow(
    context: RequestContext = Depends(get_authenticated_context),
) -> AsyncIterator[UnitOfWork]:
    """Provides a standard tenant-scoped Unit of Work transaction."""
    async with UnitOfWork(
        session_factory=async_session,
        context=context,
        is_admin=False,
    ) as uow:
        yield uow


async def get_admin_uow(
    context: RequestContext = Depends(get_authenticated_context),
) -> AsyncIterator[UnitOfWork]:
    """Provides an admin-scoped Unit of Work bypassing Row-Level Security checks."""
    if context.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required",
        )

    async with UnitOfWork(
        session_factory=async_session,
        context=context,
        is_admin=True,
    ) as uow:
        yield uow
