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
from app.modules.tenant.schemas import TenantCreate
from app.modules.tenant.services.tenant_service import TenantService
from app.utils.security import hash_password, hash_token


class RegistrationService:
    """Service to handle self-service tenant registration and joining via invitations."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.tenant_service = TenantService(uow)

    @staticmethod
    def _decode_invitation_token(token: str) -> dict:
        try:
            return jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.PyJWTError:
            raise ServiceError.bad_request("Invalid or expired invitation token")

    async def register(self, data: RegisterRequest) -> tuple[User, Tenant]:
        """Register a new Tenant organization and its first Administrator user."""
        tenant = await self.tenant_service.create(TenantCreate(name=data.tenant_name))

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

        clean_email = data.email.strip().lower()
        if clean_email != invite_email.strip().lower():
            raise ServiceError.bad_request("Email address does not match invitation")

        stmt = select(
            Invitation,
            select(User.id)
            .where(User.email == clean_email, User.tenant_id == tenant_id)
            .exists()
            .label("user_exists"),
        ).where(Invitation.id == invite_id)

        row = (await self.uow.session.execute(stmt)).first()
        if not row:
            raise ServiceError.not_found("Invitation")

        invitation, user_exists = row.tuple()

        if invitation.token_hash != hash_token(data.invite_token):
            raise ServiceError.not_found("Invitation")

        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError.bad_request(
                f"Invitation has already been {invitation.status.lower()}"
            )

        if invitation.expires_at < datetime.now(UTC):
            raise ServiceError.bad_request("Invitation token has expired")

        if user_exists:
            raise ServiceError.conflict(
                "Email is already registered in this organization"
            )

        user = User(
            tenant_id=tenant_id,
            email=data.email.strip().lower(),
            hashed_password=hash_password(data.password),
            role=invitation.role,
            is_active=True,
        )
        self.uow.session.add(user)

        invitation.status = InvitationStatus.ACCEPTED
        await self.uow.flush()

        return user
