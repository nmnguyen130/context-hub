# app/modules/auth/services/user_service.py
from datetime import UTC, datetime
from uuid import UUID
from fastapi import Depends
from sqlalchemy import func, select, update
from app.api.deps import get_uow
from app.core.enums import UserRole
from app.core.exceptions import ServiceError
from app.core.security import hash_password, verify_password
from app.core.uow import UnitOfWork
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.repository import UserRepository

class UserService:
    def __init__(self, uow: UnitOfWork = Depends(get_uow)):
        self.uow = uow

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)

    async def _count_active_admins(self, tenant_id: UUID) -> int:
        user_repo = self.uow.repo(UserRepository)
        stmt = (
            select(func.count())
            .select_from(User)
            .where(
                User.tenant_id == tenant_id,
                User.role == UserRole.ADMIN,
                User.is_active.is_(True)
            )
        )
        return await self.uow.session.scalar(stmt) or 0

    async def _revoke_sessions(self, user_id: UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None)
            )
            .values(revoked_at=self._utcnow())
        )
        await self.uow.session.execute(stmt)

    async def list_users(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        """Lists users with pagination."""
        user_repo = self.uow.repo(UserRepository)
        stmt = user_repo.query().where(User.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.uow.session.scalar(count_stmt) or 0
        result = await self.uow.session.scalars(stmt.offset(skip).limit(limit))
        return list(result), total

    async def get_user(self, tenant_id: UUID, user_id: UUID) -> User:
        """Retrieves a specific user."""
        user_repo = self.uow.repo(UserRepository)
        user = await user_repo.get(user_id)
        if not user or user.tenant_id != tenant_id:
            raise ServiceError("User not found", status_code=404)
        return user

    async def update_profile(self, user_id: UUID, data: any) -> User:
        """Updates user profile details."""
        user_repo = self.uow.repo(UserRepository)
        user = await user_repo.get(user_id)
        if not user:
            raise ServiceError("User not found", status_code=404)

        updates = data.model_dump(exclude_none=True)
        for field, value in updates.items():
            setattr(user, field, value)

        await self.uow.flush()
        return user

    async def update_role(
        self,
        tenant_id: UUID,
        target_user_id: UUID,
        data: any,
        acting_user_id: UUID,
    ) -> User:
        """Changes user role."""
        if target_user_id == acting_user_id:
            raise ServiceError("Admins cannot modify their own roles", status_code=400)

        user = await self.get_user(tenant_id, target_user_id)
        if user.role == UserRole.ADMIN and data.role != UserRole.ADMIN:
            admin_count = await self._count_active_admins(tenant_id)
            if admin_count <= 1:
                raise ServiceError(
                    "Cannot demote the only remaining active Administrator",
                    status_code=400,
                )

        user.role = UserRole(data.role)
        await self.uow.flush()
        return user

    async def change_password(self, user_id: UUID, data: any) -> None:
        """Changes user password."""
        user_repo = self.uow.repo(UserRepository)
        user = await user_repo.get(user_id)
        if not user:
            raise ServiceError("User not found", status_code=404)

        if not verify_password(data.current_password, user.hashed_password):
            raise ServiceError("Incorrect current password", status_code=400)

        user.hashed_password = hash_password(data.new_password)
        await self._revoke_sessions(user_id)
        await self.uow.flush()

    async def deactivate(
        self, tenant_id: UUID, user_id: UUID, acting_user_id: UUID
    ) -> None:
        """Deactivates a user."""
        if user_id == acting_user_id:
            raise ServiceError(
                "Admins cannot deactivate their own accounts", status_code=400
            )

        user = await self.get_user(tenant_id, user_id)
        if not user.is_active:
            return

        if user.role == UserRole.ADMIN:
            admin_count = await self._count_active_admins(tenant_id)
            if admin_count <= 1:
                raise ServiceError(
                    "Cannot deactivate the only remaining active Administrator",
                    status_code=400,
                )

        user.is_active = False
        await self._revoke_sessions(user_id)
        await self.uow.flush()

    async def reactivate(
        self, tenant_id: UUID, user_id: UUID, acting_user_id: UUID
    ) -> None:
        """Reactivates a user."""
        user = await self.get_user(tenant_id, user_id)
        if user.is_active:
            return

        user.is_active = True
        await self.uow.flush()
