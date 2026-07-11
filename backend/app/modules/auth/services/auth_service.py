# app/modules/auth/services/auth_service.py
from datetime import UTC, datetime
from uuid import UUID
from fastapi import Depends
from sqlalchemy import update
from app.api.deps import get_uow
from app.core.config import settings
from app.core.exceptions import ServiceError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.core.uow import UnitOfWork
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.repository import UserRepository, RefreshTokenRepository
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.tenant.models import Tenant
from app.modules.tenant.repository import TenantRepository

class AuthService:
    def __init__(self, uow: UnitOfWork = Depends(get_uow)):
        self.uow = uow

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)

    async def login(
        self,
        data: LoginRequest,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> TokenResponse:
        """Authenticates a user and generates tokens."""
        # Use admin UoW to bypass RLS isolation during login
        async with UnitOfWork.as_admin(
            context=self.uow._context,
            event_bus=self.uow._event_bus,
            session_factory=self.uow._session_factory,
            admin_session_factory=self.uow._admin_session_factory,
            reason="user authentication"
        ) as admin_uow:
            tenant = await admin_uow.repo(TenantRepository).get_by_slug(data.tenant_slug)
            if not tenant:
                raise ServiceError("Incorrect email, password, or tenant slug", status_code=401)
            if not tenant.is_active:
                raise ServiceError("Tenant organization is deactivated", status_code=400)

            user = await admin_uow.repo(UserRepository).get_by_email(data.email)
            if not user or user.tenant_id != tenant.id or not verify_password(data.password, user.hashed_password):
                raise ServiceError("Incorrect email, password, or tenant slug", status_code=401)

            if not user.is_active:
                raise ServiceError("User account is deactivated", status_code=400)

            user.last_login_at = self._utcnow()

            access_token = create_access_token(user.id, user.tenant_id, user.role)
            refresh_token_str, _, refresh_exp = create_refresh_token(user.id, user.tenant_id)

            refresh = RefreshToken(
                tenant_id=user.tenant_id,
                user_id=user.id,
                token_hash=hash_token(refresh_token_str),
                expires_at=refresh_exp,
                ip_address=ip_address,
                device_info=device_info,
            )
            await admin_uow.repo(RefreshTokenRepository).add(refresh)
            await admin_uow.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(
        self,
        refresh_token_str: str,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> TokenResponse:
        """Refreshes access and refresh tokens."""
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
        except Exception:
            raise ServiceError("Invalid or expired refresh token", status_code=401)

        user_id = UUID(payload["sub"])
        token_hash = hash_token(refresh_token_str)

        # Use admin UoW to verify refresh token across tenants safely
        async with UnitOfWork.as_admin(
            context=self.uow._context,
            event_bus=self.uow._event_bus,
            session_factory=self.uow._session_factory,
            admin_session_factory=self.uow._admin_session_factory,
            reason="user authentication"
        ) as admin_uow:
            stored_token = await admin_uow.repo(RefreshTokenRepository).get_active_by_hash(token_hash)
            if not stored_token or stored_token.user_id != user_id:
                raise ServiceError("Invalid or expired refresh token", status_code=401)

            if stored_token.expires_at < self._utcnow():
                raise ServiceError("Refresh token has expired", status_code=401)

            user = await admin_uow.repo(UserRepository).get(user_id)
            if not user or not user.is_active:
                raise ServiceError("User account is inactive or not found", status_code=401)

            # Revoke old token
            stored_token.revoked_at = self._utcnow()

            access_token = create_access_token(user.id, user.tenant_id, user.role)
            new_refresh_token, _, expires_at = create_refresh_token(user.id, user.tenant_id)

            refresh = RefreshToken(
                tenant_id=user.tenant_id,
                user_id=user.id,
                token_hash=hash_token(new_refresh_token),
                expires_at=expires_at,
                ip_address=ip_address,
                device_info=device_info,
            )
            await admin_uow.repo(RefreshTokenRepository).add(refresh)
            await admin_uow.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token_str: str) -> None:
        """Revokes a specific refresh token session."""
        token_hash = hash_token(refresh_token_str)
        async with UnitOfWork.as_admin(
            context=self.uow._context,
            event_bus=self.uow._event_bus,
            session_factory=self.uow._session_factory,
            admin_session_factory=self.uow._admin_session_factory,
            reason="user authentication"
        ) as admin_uow:
            token = await admin_uow.repo(RefreshTokenRepository).get_active_by_hash(token_hash)
            if token:
                token.revoked_at = self._utcnow()
                await admin_uow.commit()

    async def logout_all(self, user_id: UUID, tenant_id: UUID) -> int:
        """Revokes ALL active refresh tokens for the given user."""
        async with UnitOfWork.as_admin(
            context=self.uow._context,
            event_bus=self.uow._event_bus,
            session_factory=self.uow._session_factory,
            admin_session_factory=self.uow._admin_session_factory,
            reason="user authentication"
        ) as admin_uow:
            # Revoke all tokens for the user
            stmt = (
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None)
                )
                .values(revoked_at=self._utcnow())
            )
            result = await admin_uow.session.execute(stmt)
            await admin_uow.commit()
            return result.rowcount
