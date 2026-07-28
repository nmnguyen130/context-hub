from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.core.pagination import PaginationParams
from app.core.uow import UnitOfWork
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import ChangePasswordRequest, UserUpdate
from app.utils.security import hash_password, verify_password


class UserService:
    """Service to handle user management actions like list, role modification, password updates, and deactivation."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def _count_active_admins(self, tenant_id: UUID) -> int:
        stmt = select(func.count(User.id)).where(
            User.tenant_id == tenant_id,
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
        return await self.uow.session.scalar(stmt) or 0

    async def _revoke_sessions(self, user_id: UUID, tenant_id: UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.tenant_id == tenant_id,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self.uow.session.execute(stmt)

    async def list_users(
        self,
        tenant_id: UUID,
        pagination: PaginationParams | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        """List users belonging to a tenant organization with pagination."""
        pagination = pagination or PaginationParams()
        stmt = select(User).where(User.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.uow.session.scalar(count_stmt) or 0

        paginated = stmt.offset(pagination.offset).limit(pagination.limit)
        items = (await self.uow.session.scalars(paginated)).all()
        return list(items), total

    async def get_user(self, user_id: UUID) -> User:
        """Retrieve a single user, raising 404 if not found."""
        user = await self.uow.session.get(User, user_id)
        if not user:
            raise ServiceError("User not found", status_code=404)
        return user

    async def update_role(
        self,
        target_user_id: UUID,
        data: UserUpdate,
        acting_user_id: UUID,
        acting_user_role: UserRole,
    ) -> User:
        """Modify a user's role, enforcing role hierarchy and self-modification blocks."""
        if target_user_id == acting_user_id:
            raise ServiceError("Admins cannot modify their own roles", status_code=400)

        user = await self.get_user(target_user_id)

        # Enforce role hierarchy: acting user must be higher authority than target user
        if not acting_user_role.has_higher_privilege_than(user.role):
            raise ServiceError(
                "Cannot modify a user with equal or higher authority", status_code=403
            )

        # Enforce target role limit: acting user cannot assign a role higher than their own
        if data.role.priority > acting_user_role.priority:
            raise ServiceError(
                "Cannot assign a role higher than your own", status_code=403
            )

        if user.role == UserRole.ADMIN and data.role != UserRole.ADMIN:
            admin_count = await self._count_active_admins(user.tenant_id)
            if admin_count <= 1:
                raise ServiceError(
                    "Cannot demote the only remaining active Administrator",
                    status_code=400,
                )

        user.role = data.role
        await self.uow.flush()
        return user

    async def change_password(self, user_id: UUID, data: ChangePasswordRequest) -> None:
        """Update a user's password, forcing a revocation of all active sessions."""
        user = await self.get_user(user_id)

        if not verify_password(data.current_password, user.hashed_password):
            raise ServiceError("Incorrect current password", status_code=400)

        user.hashed_password = hash_password(data.new_password)
        await self._revoke_sessions(user_id, user.tenant_id)
        await self.uow.flush()

    async def deactivate(
        self,
        user_id: UUID,
        acting_user_id: UUID,
        acting_user_role: UserRole,
    ) -> None:
        """Deactivate a user's account and revoke their active sessions, enforcing role hierarchy."""
        if user_id == acting_user_id:
            raise ServiceError(
                "Admins cannot deactivate their own accounts", status_code=400
            )

        user = await self.get_user(user_id)
        if not user.is_active:
            return

        # Enforce role hierarchy: acting user must be higher authority than target user
        if not acting_user_role.has_higher_privilege_than(user.role):
            raise ServiceError(
                "Cannot deactivate a user with equal or higher authority",
                status_code=403,
            )

        if user.role == UserRole.ADMIN:
            admin_count = await self._count_active_admins(user.tenant_id)
            if admin_count <= 1:
                raise ServiceError(
                    "Cannot deactivate the only remaining active Administrator",
                    status_code=400,
                )

        user.is_active = False
        await self._revoke_sessions(user_id, user.tenant_id)
        await self.uow.flush()

    async def reactivate(
        self,
        user_id: UUID,
        acting_user_role: UserRole,
    ) -> None:
        """Reactivate a deactivated user's account, enforcing role hierarchy."""
        user = await self.get_user(user_id)
        if user.is_active:
            return

        # Enforce role hierarchy: acting user must be higher authority than target user
        if not acting_user_role.has_higher_privilege_than(user.role):
            raise ServiceError(
                "Cannot reactivate a user with equal or higher authority",
                status_code=403,
            )

        user.is_active = True
        await self.uow.flush()
