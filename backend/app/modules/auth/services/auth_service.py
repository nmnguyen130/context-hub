from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.exceptions import ServiceError
from app.core.uow import UnitOfWork
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.tenant.models import Tenant
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)


class AuthService:
    """Service to handle user authentication, session refresh, and logout."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def login(self, data: LoginRequest, tenant_slug: str) -> TokenResponse:
        """Authenticate a user, update last login timestamp, and issue JWT tokens."""
        clean_email = data.email.strip().lower()
        clean_slug = tenant_slug.strip().lower()

        tenant = await self.uow.session.scalar(
            select(Tenant).where(
                Tenant.slug == clean_slug,
                Tenant.is_active.is_(True),
            )
        )
        if not tenant:
            raise ServiceError.unauthorized("Incorrect email, password, or tenant slug")

        user = await self.uow.session.scalar(
            select(User).where(
                User.tenant_id == tenant.id,
                User.email == clean_email,
                User.is_active.is_(True),
            )
        )
        if not user:
            raise ServiceError.unauthorized("Incorrect email, password, or tenant slug")
        if not verify_password(data.password, user.hashed_password):
            raise ServiceError.unauthorized("Incorrect email, password, or tenant slug")

        user.last_login_at = datetime.now(UTC)

        access_token = create_access_token(
            user.id, user.tenant_id, user.role, plan=tenant.plan_tier
        )
        refresh_token_str, _, refresh_exp = create_refresh_token(
            user.id, user.tenant_id
        )

        refresh = RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hash_token(refresh_token_str),
            expires_at=refresh_exp,
        )
        self.uow.session.add(refresh)
        await self.uow.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        )

    async def refresh(self, refresh_token_str: str) -> TokenResponse:
        """Validate a refresh token and issue a new access/refresh token pair."""
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
        except Exception:
            raise ServiceError.unauthorized("Invalid or expired refresh token")

        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
        token_hash = hash_token(refresh_token_str)

        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.tenant_id == tenant_id,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > func.now(),
        )
        stored_token = await self.uow.session.scalar(stmt)
        if not stored_token:
            raise ServiceError.unauthorized("Invalid or expired refresh token")

        user = await self.uow.session.get(User, user_id)
        tenant = await self.uow.session.get(Tenant, tenant_id)

        if not user.is_active or not tenant.is_active:
            raise ServiceError.unauthorized("Account or organization is inactive")

        stored_token.revoked_at = datetime.now(UTC)

        access_token = create_access_token(
            user.id, user.tenant_id, user.role, plan=tenant.plan_tier
        )
        new_refresh_token, _, expires_at = create_refresh_token(user.id, user.tenant_id)

        new_stored_token = RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            expires_at=expires_at,
        )
        self.uow.session.add(new_stored_token)
        await self.uow.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def logout(self, refresh_token_str: str) -> None:
        """Revoke an active refresh token session."""
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
            tenant_id = UUID(payload["tenant_id"])
        except Exception:
            raise ServiceError.bad_request("Invalid refresh token")

        token_hash = hash_token(refresh_token_str)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.tenant_id == tenant_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self.uow.session.execute(stmt)
        await self.uow.flush()

    async def logout_all(self, tenant_id: UUID, user_id: UUID) -> int:
        """Revoke all active refresh token sessions for a user within a tenant."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.tenant_id == tenant_id,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        result = await self.uow.session.execute(stmt)
        await self.uow.flush()
        return result.rowcount
