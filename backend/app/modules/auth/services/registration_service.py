from datetime import UTC, datetime
from uuid import UUID

import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.core.uow import UnitOfWork
from app.modules.auth.models import Invitation, InvitationStatus, User
from app.modules.auth.schemas import InvitationAccept, RegisterRequest
from app.modules.tenant.models import Tenant
from app.modules.tenant.services.tenant_service import TenantService
from app.utils.security import hash_password, hash_token


class RegistrationService:
    """Service to handle self-service tenant registration and joining via invitations."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    @staticmethod
    def _decode_invitation_token(token: str) -> dict:
        try:
            return jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.PyJWTError:
            raise ServiceError("Invalid or expired invitation token", status_code=400)

    async def register(self, data: RegisterRequest) -> tuple[User, Tenant]:
        """Register a new Tenant organization and its first Administrator user."""
        slug = TenantService.generate_slug(data.tenant_name)

        # Check if tenant already exists
        existing_tenant = await self.uow.session.scalar(
            select(Tenant).where(Tenant.slug == slug)
        )
        if existing_tenant:
            raise ServiceError("Tenant with this name or slug already exists", status_code=409)

        # Create Tenant
        tenant = Tenant(
            name=data.tenant_name.strip(),
            slug=slug,
        )
        self.uow.session.add(tenant)
        await self.uow.flush()

        # Create Admin User under the new Tenant
        user = User(
            tenant_id=tenant.id,
            email=data.email.strip().lower(),
            hashed_password=hash_password(data.password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.uow.session.add(user)
        await self.uow.flush()

        return user, tenant

    async def join_via_invitation(self, data: InvitationAccept) -> User:
        """Register a new User in an existing Tenant using a valid invitation token."""
        payload = self._decode_invitation_token(data.invite_token)
        invite_id = UUID(payload["invite_id"])
        tenant_id = UUID(payload["tenant_id"])
        invite_email = payload["email"]

        if data.email.strip().lower() != invite_email.strip().lower():
            raise ServiceError("Email address does not match invitation", status_code=400)

        invitation = await self.uow.session.get(Invitation, invite_id)
        if not invitation or invitation.token_hash != hash_token(data.invite_token):
            raise ServiceError("Invitation not found or token modified", status_code=404)

        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError(f"Invitation has already been {invitation.status.lower()}", status_code=400)

        if invitation.expires_at < datetime.now(UTC):
            raise ServiceError("Invitation token has expired", status_code=400)

        # Check if user already exists
        existing_user = await self.uow.session.scalar(
            select(User).where(
                User.email == data.email.strip().lower(),
                User.tenant_id == tenant_id,
            )
        )
        if existing_user:
            raise ServiceError("Email is already registered in this organization", status_code=409)

        # Create User
        user = User(
            tenant_id=tenant_id,
            email=data.email.strip().lower(),
            hashed_password=hash_password(data.password),
            role=invitation.role,
            is_active=True,
        )
        self.uow.session.add(user)

        # Mark invitation as accepted
        invitation.status = InvitationStatus.ACCEPTED
        await self.uow.flush()

        return user
