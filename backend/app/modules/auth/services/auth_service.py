from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ServiceError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.tenant.models import Tenant


from fastapi import Depends
from app.api.deps import get_db


class AuthService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def login(
        self,
        data: LoginRequest,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> TokenResponse:
        """Authenticates a user, updates login history, creates access/refresh tokens."""
        # 1. Resolve tenant by slug
        tenant_stmt = (
            select(Tenant)
            .where(Tenant.slug == data.tenant_slug)
            .execution_options(skip_tenant_filter=True)
        )
        tenant = (await self.db.execute(tenant_stmt)).scalar_one_or_none()
        if not tenant:
            raise ServiceError(
                "Incorrect email, password, or tenant slug", status_code=401
            )

        if not tenant.is_active:
            raise ServiceError("Tenant organization is deactivated", status_code=400)

        # 2. Find user by email and tenant_id
        user_stmt = (
            select(User)
            .where(User.email == data.email, User.tenant_id == tenant.id)
            .execution_options(skip_tenant_filter=True)
        )
        user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if not user:
            raise ServiceError(
                "Incorrect email, password, or tenant slug", status_code=401
            )

        # 3. Verify password
        if not verify_password(data.password, user.password_hash):
            raise ServiceError(
                "Incorrect email, password, or tenant slug", status_code=401
            )

        # 4. Check if active
        if not user.is_active:
            raise ServiceError("User account is deactivated", status_code=400)

        # 5. Update last_login_at
        user.last_login_at = datetime.now(UTC)
        self.db.add(user)

        # 6. Generate tokens
        access_token = create_access_token(user.id, user.tenant_id, user.role)
        refresh_token_str, refresh_jti, refresh_exp = create_refresh_token(
            user.id, user.tenant_id
        )

        # 7. Store hashed refresh token in DB
        hashed_rt = hash_token(refresh_token_str)
        db_refresh = RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hashed_rt,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=refresh_exp,
        )
        self.db.add(db_refresh)

        # 8. Record audit log
        await AuditService(self.db).log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="USER_LOGIN",
            ip_address=ip_address,
        )

        await self.db.flush()

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
        """Refreshes access and refresh tokens. Supports token rotation and theft detection."""
        # 1. Decode token JWT to verify signature and expiration
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
        except Exception:
            raise ServiceError("Invalid or expired refresh token", status_code=401)

        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

        # 2. Look up the token in the DB by hash
        rt_hash = hash_token(refresh_token_str)
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == rt_hash)
            .execution_options(skip_tenant_filter=True)
        )
        db_token = (await self.db.execute(stmt)).scalar_one_or_none()

        if not db_token:
            raise ServiceError("Invalid or expired refresh token", status_code=401)

        # 3. Theft detection: if already revoked, revoke ALL user sessions
        if db_token.is_revoked:
            # Revoke all tokens for this user
            revoke_all_stmt = (
                update(RefreshToken)
                .where(RefreshToken.user_id == user_id)
                .values(revoked_at=datetime.now(UTC))
                .execution_options(skip_tenant_filter=True)
            )
            await self.db.execute(revoke_all_stmt)
            await self.db.flush()

            await AuditService(self.db).log(
                tenant_id=tenant_id,
                user_id=user_id,
                action="REFRESH_TOKEN_REUSE_DETECTED",
                ip_address=ip_address,
                payload_diff={"token_id": str(db_token.id)},
            )
            raise ServiceError(
                "Token reuse detected. All sessions revoked.", status_code=401
            )

        # Check expiration
        if db_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise ServiceError("Refresh token has expired", status_code=401)

        # Verify matching user
        user_stmt = (
            select(User)
            .where(User.id == user_id)
            .execution_options(skip_tenant_filter=True)
        )
        user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if not user or not user.is_active:
            raise ServiceError("User account is inactive or not found", status_code=401)

        # 4. Revoke current token (rotation)
        db_token.revoked_at = datetime.now(UTC)
        self.db.add(db_token)

        # 5. Generate new pair
        access_token = create_access_token(user.id, user.tenant_id, user.role)
        new_rt_str, new_rt_jti, new_rt_exp = create_refresh_token(
            user.id, user.tenant_id
        )

        # Store new refresh token
        new_rt_hash = hash_token(new_rt_str)
        new_db_token = RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=new_rt_hash,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=new_rt_exp,
        )
        self.db.add(new_db_token)
        await self.db.flush()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_rt_str,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token_str: str) -> None:
        """Revokes a specific refresh token session."""
        try:
            payload = decode_token(refresh_token_str, expected_type="refresh")
        except Exception:
            raise ServiceError("Invalid refresh token", status_code=400)

        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
        rt_hash = hash_token(refresh_token_str)

        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == rt_hash)
            .execution_options(skip_tenant_filter=True)
        )
        db_token = (await self.db.execute(stmt)).scalar_one_or_none()

        if db_token and not db_token.is_revoked:
            db_token.revoked_at = datetime.now(UTC)
            self.db.add(db_token)

            await AuditService(self.db).log(
                tenant_id=tenant_id,
                user_id=user_id,
                action="USER_LOGOUT",
            )
            await self.db.flush()

    async def logout_all(self, user_id: UUID, tenant_id: UUID) -> int:
        """Revokes ALL active refresh tokens for the given user."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
            .execution_options(skip_tenant_filter=True)
        )
        result = await self.db.execute(stmt)
        count = result.rowcount

        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=user_id,
            action="USER_LOGOUT_ALL",
        )
        await self.db.flush()
        return count
