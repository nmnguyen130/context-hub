from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    Token,
    UserJoin,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.modules.auth.services import authenticate_user, join_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def api_register_user(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Registers a new Tenant organization and its primary Administrator user.
    """
    user = await register_user(db, data)
    return user


@router.post(
    "/register/join", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def api_join_user(data: UserJoin, db: AsyncSession = Depends(get_db)):
    """
    Registers a new employee user into an existing Tenant using a signed invitation token.
    """
    user = await join_user(db, data)
    return user


@router.post("/login", response_model=Token)
async def api_login_user(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Standard JSON body credentials login.
    """
    user = await authenticate_user(db, data)
    access_token = create_access_token(user.id, user.tenant_id, user.role)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def api_get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieves the currently authenticated user's profile.
    """
    return current_user
