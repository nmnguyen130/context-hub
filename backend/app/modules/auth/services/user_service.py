from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.exceptions import ServiceError
from app.core.security import hash_password, verify_password
from app.modules.audit.service import AuditService
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    UserRoleUpdateRequest,
    UserUpdateRequest,
)


from fastapi import Depends
from app.api.deps import get_db


class UserService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def list_users(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        """Lists users in the tenant with pagination and optional status filter."""
        query = select(User).where(User.tenant_id == tenant_id)
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_count = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginated fetch
        query = query.offset(skip).limit(limit)
        users = list((await self.db.execute(query)).scalars().all())

        return users, total_count

    async def get_user(self, tenant_id: UUID, user_id: UUID) -> User:
        """Retrieves a specific user within a tenant."""
        stmt = select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        user = (await self.db.execute(stmt)).scalar_one_or_none()
        if not user:
            raise ServiceError("User not found", status_code=404)
        return user

    async def update_profile(self, user_id: UUID, data: UserUpdateRequest) -> User:
        """Self-service profile update (first name, last name)."""
        # User is already scoped to their own id, but let's load
        stmt = (
            select(User)
            .where(User.id == user_id)
            .execution_options(skip_tenant_filter=True)
        )
        user = (await self.db.execute(stmt)).scalar_one_or_none()
        if not user:
            raise ServiceError("User not found", status_code=404)

        if data.first_name is not None:
            user.first_name = data.first_name
        if data.last_name is not None:
            user.last_name = data.last_name

        self.db.add(user)

        # Log Audit
        await AuditService(self.db).log(
            tenant_id=user.tenant_id,
            user_id=user_id,
            action="USER_UPDATE_PROFILE",
        )
        await self.db.flush()
        return user

    async def update_role(
        self,
        tenant_id: UUID,
        target_user_id: UUID,
        data: UserRoleUpdateRequest,
        acting_user_id: UUID,
    ) -> User:
        """Admin-only: change a user's role. Prevents self-demoting or removing the last admin."""
        if target_user_id == acting_user_id:
            raise ServiceError("Admins cannot modify their own roles", status_code=400)

        target_user = await self.get_user(tenant_id, target_user_id)
        old_role = target_user.role

        # If demoting target user from ADMIN to something else, check if they are the last admin
        if old_role == UserRole.ADMIN and data.role != UserRole.ADMIN:
            admin_stmt = (
                select(func.count())
                .select_from(User)
                .where(
                    User.tenant_id == tenant_id,
                    User.role == UserRole.ADMIN,
                    User.is_active == True,
                )
                .execution_options(skip_tenant_filter=True)
            )
            admin_count = (await self.db.execute(admin_stmt)).scalar() or 0
            if admin_count <= 1:
                raise ServiceError(
                    "Cannot demote the only remaining active Administrator",
                    status_code=400,
                )

        target_user.role = UserRole(data.role)
        self.db.add(target_user)

        # Log Audit
        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=acting_user_id,
            action="USER_ROLE_CHANGE",
            resource_type="User",
            resource_id=target_user_id,
            payload_diff={"before": old_role, "after": data.role},
        )
        await self.db.flush()
        return target_user

    async def change_password(self, user_id: UUID, data: ChangePasswordRequest) -> None:
        """User changes their own password after verifying their current password."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .execution_options(skip_tenant_filter=True)
        )
        user = (await self.db.execute(stmt)).scalar_one_or_none()
        if not user:
            raise ServiceError("User not found", status_code=404)

        if not verify_password(data.current_password, user.password_hash):
            raise ServiceError("Incorrect current password", status_code=400)

        user.password_hash = hash_password(data.new_password)
        self.db.add(user)

        # Log Audit
        await AuditService(self.db).log(
            tenant_id=user.tenant_id,
            user_id=user_id,
            action="USER_PASSWORD_CHANGE",
        )

        # Revoke all sessions for security on password change
        revoke_sessions_stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(revoked_at=datetime.now(UTC))
            .execution_options(skip_tenant_filter=True)
        )
        await self.db.execute(revoke_sessions_stmt)
        await self.db.flush()

    async def deactivate(
        self, tenant_id: UUID, user_id: UUID, acting_user_id: UUID
    ) -> None:
        """Admin-only: deactivate a user. Prevents self-deactivation or deactivating the last admin."""
        if user_id == acting_user_id:
            raise ServiceError(
                "Admins cannot deactivate their own accounts", status_code=400
            )

        user = await self.get_user(tenant_id, user_id)
        if not user.is_active:
            return  # Already deactivated

        # If deactivating an ADMIN, check if they are the last active admin
        if user.role == UserRole.ADMIN:
            admin_stmt = (
                select(func.count())
                .select_from(User)
                .where(
                    User.tenant_id == tenant_id,
                    User.role == UserRole.ADMIN,
                    User.is_active == True,
                )
                .execution_options(skip_tenant_filter=True)
            )
            admin_count = (await self.db.execute(admin_stmt)).scalar() or 0
            if admin_count <= 1:
                raise ServiceError(
                    "Cannot deactivate the only remaining active Administrator",
                    status_code=400,
                )

        user.is_active = False
        self.db.add(user)

        # Log Audit
        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=acting_user_id,
            action="USER_DEACTIVATE",
            resource_type="User",
            resource_id=user_id,
        )

        # Revoke all active refresh tokens for the user
        revoke_sessions_stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(revoked_at=datetime.now(UTC))
            .execution_options(skip_tenant_filter=True)
        )
        await self.db.execute(revoke_sessions_stmt)
        await self.db.flush()

    async def reactivate(
        self, tenant_id: UUID, user_id: UUID, acting_user_id: UUID
    ) -> None:
        """Admin-only: reactivates a deactivated user."""
        user = await self.get_user(tenant_id, user_id)
        if user.is_active:
            return  # Already active

        user.is_active = True
        self.db.add(user)

        # Log Audit
        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=acting_user_id,
            action="USER_REACTIVATE",
            resource_type="User",
            resource_id=user_id,
        )
        await self.db.flush()
