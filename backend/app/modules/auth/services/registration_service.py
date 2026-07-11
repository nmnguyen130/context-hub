# app/modules/auth/services/registration_service.py
from datetime import UTC, datetime
from uuid import UUID
import jwt
from fastapi import Depends
from app.api.deps import get_uow
from app.core.config import settings
from app.core.enums import InvitationStatus, PlanTier, UserRole
from app.core.exceptions import ServiceError
from app.core.security import hash_password, hash_token
from app.core.uow import UnitOfWork
from app.modules.auth.models import Invitation, User
from app.modules.auth.schemas import JoinRequest, RegisterRequest
from app.modules.auth.repository import InvitationRepository, UserRepository
from app.modules.tenant.models import Tenant
from app.modules.tenant.repository import TenantRepository
from app.modules.tenant.services.tenant_service import TenantService

class RegistrationService:
    def __init__(self, uow: UnitOfWork = Depends(get_uow)):
        self.uow = uow

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)

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
        """Registers a new tenant and its admin user."""
        slug = TenantService.generate_slug(data.tenant_name)

        async with UnitOfWork.as_admin(
            context=self.uow._context,
            event_bus=self.uow._event_bus,
            session_factory=self.uow._session_factory,
            admin_session_factory=self.uow._admin_session_factory,
            reason="new tenant registration"
        ) as admin_uow:
            existing = await admin_uow.repo(TenantRepository).get_by_slug(slug)
            if existing:
                raise ServiceError(
                    "Tenant with this name or slug already exists", status_code=409
                )

            tenant = Tenant(
                name=data.tenant_name,
                slug=slug,
                plan_tier=PlanTier.STARTER,
                settings={},
            )
            await admin_uow.repo(TenantRepository).add(tenant)
            await admin_uow.flush()

            user = User(
                tenant_id=tenant.id,
                email=data.email,
                hashed_password=hash_password(data.password),
                first_name=data.first_name,
                last_name=data.last_name,
                role=UserRole.ADMIN,
                is_active=True,
            )
            await admin_uow.repo(UserRepository).add(user)
            await admin_uow.commit()

        return user, tenant

    async def join_via_invitation(self, data: JoinRequest) -> User:
        """Registers a user via invitation."""
        payload = self._decode_invitation_token(data.invite_token)
        invite_id = UUID(payload["invite_id"])
        tenant_id = UUID(payload["tenant_id"])
        invite_email = payload["email"]

        if data.email != invite_email:
            raise ServiceError(
                "Email address does not match invitation", status_code=400
            )

        async with UnitOfWork.as_admin(
            context=self.uow._context,
            event_bus=self.uow._event_bus,
            session_factory=self.uow._session_factory,
            admin_session_factory=self.uow._admin_session_factory,
            reason="new tenant registration"
        ) as admin_uow:
            invitation = await admin_uow.repo(InvitationRepository).get(invite_id)
            if not invitation or invitation.token_hash != hash_token(data.invite_token):
                raise ServiceError(
                    "Invitation not found or token modified", status_code=404
                )

            if invitation.status != InvitationStatus.PENDING:
                raise ServiceError(
                    f"Invitation has already been {invitation.status.lower()}",
                    status_code=400,
                )

            if invitation.expires_at < self._utcnow():
                invitation.status = InvitationStatus.EXPIRED
                await admin_uow.commit()
                raise ServiceError("Invitation token has expired", status_code=400)

            user_repo = admin_uow.repo(UserRepository)
            existing_user = await user_repo.get_by_email(data.email)
            if existing_user and existing_user.tenant_id == tenant_id:
                raise ServiceError(
                    "Email is already registered in this organization", status_code=409
                )

            user = User(
                tenant_id=tenant_id,
                email=data.email,
                hashed_password=hash_password(data.password),
                first_name=data.first_name,
                last_name=data.last_name,
                role=invitation.role,
                is_active=True,
            )
            await user_repo.add(user)
            invitation.status = InvitationStatus.ACCEPTED
            await admin_uow.commit()

        return user
