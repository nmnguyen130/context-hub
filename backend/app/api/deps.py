from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import AuthContext
from app.core.config import settings
from app.core.enums import UserRole
from app.infrastructure.container import RAGContainer
from app.modules.auth.models import User


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped session from the lifespan-managed pool."""
    async with request.app.state.db.session_factory() as session:
        async with session.begin():
            yield session


def get_infra(request: Request, db: AsyncSession = Depends(get_db)) -> RAGContainer:
    return RAGContainer(
        db=db,
        redis=request.app.state.redis,
        storage=request.app.state.storage,
    )


# OAuth2 scheme configuration
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
)


async def get_auth_context(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> AuthContext:
    """Retrieves the pre-resolved stateless authentication context from request state."""
    identity = getattr(request.state, "identity", None)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return identity


async def get_current_user(
    auth_ctx: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Returns the authenticated User by fetching from the database."""
    # Ensure User query is scoped to their tenant via default criteria or manual filter
    # But since it's global email check, let's load it directly.
    stmt = select(User).where(User.id == auth_ctx.user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verifies that the user has ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required",
        )
    return current_user
