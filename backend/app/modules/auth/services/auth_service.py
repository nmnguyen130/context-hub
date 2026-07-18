from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

from app.core.exceptions import ServiceError
from app.core.uow import UnitOfWork
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.tenant.services import TenantService
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
        self.tenant_service = TenantService(uow)

    async def login(self, data: LoginRequest, tenant_slug: str) -> TokenResponse:
        """Authenticate a user, update last login timestamp, and issue JWT tokens."""
        # 1. Resolve Tenant
        tenant = await self.tenant_service.get_by_slug(tenant_slug)
        if not tenant or not tenant.is_active:
            raise ServiceError(
                "Incorrect email, password, or tenant slug", status_code=401
            )

        # 2. Resolve User within the resolved tenant
        user = await self.uow.session.scalar(
            select(User).where(
                User.email == data.email.strip().lower(),
                User.tenant_id == tenant.id,
            )
        )
        if (
            not user
            or not verify_password(data.password, user.hashed_password)
            or not user.is_active
        ):
            raise ServiceError(
                "Incorrect email, password, or tenant slug", status_code=401
            )

        # 3. Update last login timestamp
        user.last_login_at = datetime.now(UTC)

        # 4. Generate JWT tokens
        access_token = create_access_token(
            user.id, user.tenant_id, user.role, plan=tenant.plan_tier
        )
        refresh_token_str, _, refresh_exp = create_refresh_token(
            user.id, user.tenant_id
        )

        # 5. Persist refresh token session
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
            raise ServiceError("Invalid or expired refresh token", status_code=401)

        user_id = UUID(payload["sub"])
        token_hash = hash_token(refresh_token_str)

        # Retrieve active stored token
        stored_token = await self.uow.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        if not stored_token or stored_token.user_id != user_id:
            raise ServiceError("Invalid or expired refresh token", status_code=401)

        if stored_token.expires_at < datetime.now(UTC):
            raise ServiceError("Refresh token has expired", status_code=401)

        # Get User details
        user = await self.uow.session.get(User, user_id)
        if not user or not user.is_active:
            raise ServiceError("User account is inactive or not found", status_code=401)

        # Get Tenant details to check active status and get plan_tier
        tenant = await self.tenant_service.get_by_id(user.tenant_id)
        if not tenant or not tenant.is_active:
            raise ServiceError(
                "Tenant organization is inactive or not found", status_code=401
            )

        # Revoke old refresh token
        stored_token.revoked_at = datetime.now(UTC)

        # Issue new token pair
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
        """Revoke an active refresh token session, marking it as logged out."""
        token_hash = hash_token(refresh_token_str)
        token = await self.uow.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        if token:
            token.revoked_at = datetime.now(UTC)
            await self.uow.flush()

    async def logout_all_devices(self, user_id: UUID) -> int:
        """Revoke all active refresh token sessions for a specific user."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        result = await self.uow.session.execute(stmt)
        await self.uow.flush()
        return result.rowcount
