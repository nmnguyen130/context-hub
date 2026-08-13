from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.core.pagination import CursorParams, paginate_cursor
from app.core.uow import UnitOfWork
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import ChangePasswordRequest, UserUpdate
from app.utils.security import hash_password, verify_password


class UserService:
    """Service to handle user management actions like list, role modification, password updates, and deactivation."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def _revoke_sessions(self, user_id: UUID, tenant_id: UUID) -> None:
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
        await self.uow.session.execute(stmt)

    async def _count_active_admins(self, tenant_id: UUID) -> int:
        stmt = select(func.count(User.id)).where(
            User.tenant_id == tenant_id,
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
        return await self.uow.session.scalar(stmt) or 0

    async def list_users(
        self,
        tenant_id: UUID,
        params: CursorParams | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[User], str | None, bool]:
        """List users belonging to a tenant organization with pagination."""
        params = params or CursorParams()
        stmt = select(User).where(User.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        return await paginate_cursor(
            self.uow.session,
            stmt,
            params,
            sort_column=User.created_at,
            id_column=User.id,
        )

    async def get_user(self, user_id: UUID) -> User:
        """Retrieve a single user, raising 404 if not found."""
        user = await self.uow.session.get(User, user_id)
        if not user:
            raise ServiceError.not_found("User")
        return user

    async def update_role(
        self,
        target_user_id: UUID,
        data: UserUpdate,
        acting_user_id: UUID,
        acting_user_role: UserRole,
    ) -> User:
        """Modify a user's role, enforcing role hierarchy and self-modification blocks."""
        user = await self.get_user(target_user_id)

        if data.display_name is not None:
            user.display_name = data.display_name.strip() or None
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url.strip() or None

        if data.role is not None:
            if target_user_id == acting_user_id:
                raise ServiceError.bad_request("Admins cannot modify their own roles")

            if not acting_user_role.has_higher_privilege_than(user.role):
                raise ServiceError.forbidden(
                    "Cannot modify a user with equal or higher authority"
                )

            if data.role.priority > acting_user_role.priority:
                raise ServiceError.forbidden("Cannot assign a role higher than your own")

            if user.role == UserRole.ADMIN and data.role != UserRole.ADMIN:
                admin_count = await self._count_active_admins(user.tenant_id)
                if admin_count <= 1:
                    raise ServiceError.bad_request(
                        "Cannot demote the only remaining active Administrator"
                    )

            user.role = data.role

        await self.uow.flush()
        return user

    async def change_password(self, user_id: UUID, data: ChangePasswordRequest) -> None:
        """Update a user's password, forcing a revocation of all active sessions."""
        user = await self.get_user(user_id)

        if not verify_password(data.current_password, user.hashed_password):
            raise ServiceError.bad_request("Incorrect current password")

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
            raise ServiceError.bad_request(
                "Admins cannot deactivate their own accounts"
            )

        user = await self.get_user(user_id)
        if not user.is_active:
            return

        if not acting_user_role.has_higher_privilege_than(user.role):
            raise ServiceError.forbidden(
                "Cannot deactivate a user with equal or higher authority"
            )

        if user.role == UserRole.ADMIN:
            admin_count = await self._count_active_admins(user.tenant_id)
            if admin_count <= 1:
                raise ServiceError.bad_request(
                    "Cannot deactivate the only remaining active Administrator"
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

        if not acting_user_role.has_higher_privilege_than(user.role):
            raise ServiceError.forbidden(
                "Cannot reactivate a user with equal or higher authority"
            )

        user.is_active = True
        await self.uow.flush()
