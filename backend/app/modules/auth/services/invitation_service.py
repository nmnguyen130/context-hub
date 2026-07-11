# app/modules/auth/services/invitation_service.py
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID
import jwt
from fastapi import Depends
from sqlalchemy import select
from app.api.deps import get_uow
from app.core.config import settings
from app.core.enums import InvitationStatus, UserRole
from app.core.exceptions import ServiceError
from app.core.security import hash_token
from app.core.uow import UnitOfWork
from app.modules.auth.models import Invitation, User
from app.modules.auth.schemas import InvitationCreateRequest
from app.modules.auth.repository import InvitationRepository, UserRepository

class InvitationService:
    def __init__(self, uow: UnitOfWork = Depends(get_uow)):
        self.uow = uow

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _create_invitation_token(
        invitation_id: UUID,
        tenant_id: UUID,
        email: str,
        role: UserRole,
        expires_at: datetime,
    ) -> str:
        payload = {
            "invite_id": str(invitation_id),
            "tenant_id": str(tenant_id),
            "email": email,
            "role": role,
            "exp": expires_at,
        }
        return jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    async def create_invitation(
        self,
        tenant_id: UUID,
        invited_by: UUID,
        data: InvitationCreateRequest,
        expires_in_days: int = 7,
    ) -> tuple[Invitation, str]:
        """Creates a new invitation."""
        user_repo = self.uow.repo(UserRepository)
        invite_repo = self.uow.repo(InvitationRepository)

        # Check if user already exists
        if await user_repo.get_by_email(data.email):
            raise ServiceError(
                "User with this email is already a member", status_code=409
            )

        # Check for existing pending invitation
        stmt = invite_repo.query().where(
            Invitation.email == data.email,
            Invitation.tenant_id == tenant_id,
            Invitation.status == InvitationStatus.PENDING
        )
        pending = await self.uow.session.scalar(stmt)
        if pending:
            if pending.expires_at >= self._utcnow():
                raise ServiceError(
                    "A pending invitation already exists", status_code=409
                )
            pending.status = InvitationStatus.EXPIRED

        invitation_id = uuid.uuid4()
        expires_at = self._utcnow() + timedelta(days=expires_in_days)
        token = self._create_invitation_token(
            invitation_id, tenant_id, data.email, data.role, expires_at
        )
        invitation = Invitation(
            id=invitation_id,
            tenant_id=tenant_id,
            invited_by=invited_by,
            email=data.email,
            role=data.role,
            status=InvitationStatus.PENDING,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )
        await invite_repo.add(invitation)
        await self.uow.flush()
        return invitation, token

    async def list_invitations(
        self,
        tenant_id: UUID,
        status: InvitationStatus | None = None,
    ) -> list[Invitation]:
        """Lists invitations."""
        invite_repo = self.uow.repo(InvitationRepository)
        stmt = invite_repo.query().where(Invitation.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Invitation.status == status)
        result = await self.uow.session.scalars(stmt)
        return list(result)

    async def get_invitation_by_id(
        self, tenant_id: UUID, invitation_id: UUID
    ) -> Invitation:
        invite_repo = self.uow.repo(InvitationRepository)
        invitation = await invite_repo.get(invitation_id)
        if not invitation or invitation.tenant_id != tenant_id:
            raise ServiceError("Invitation not found", status_code=404)
        return invitation

    async def revoke_invitation(self, tenant_id: UUID, invitation_id: UUID) -> None:
        """Revokes a pending invitation."""
        invitation = await self.get_invitation_by_id(tenant_id, invitation_id)

        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError("Cannot revoke this invitation", status_code=400)
        invitation.status = InvitationStatus.REVOKED
        await self.uow.flush()

    async def resend_invitation(
        self,
        tenant_id: UUID,
        invitation_id: UUID,
        resending_user_id: UUID,
        expires_in_days: int = 7,
    ) -> tuple[Invitation, str]:
        """Revokes the old invitation token and creates a new one with a fresh expiry."""
        invitation = await self.get_invitation_by_id(tenant_id, invitation_id)
        if invitation.status not in (
            InvitationStatus.PENDING,
            InvitationStatus.EXPIRED,
        ):
            raise ServiceError("Cannot resend this invitation", status_code=400)

        expires_at = self._utcnow() + timedelta(days=expires_in_days)
        token = self._create_invitation_token(
            invitation.id,
            tenant_id,
            invitation.email,
            invitation.role,
            expires_at,
        )
        invitation.token_hash = hash_token(token)
        invitation.expires_at = expires_at
        invitation.status = InvitationStatus.PENDING
        invitation.invited_by = resending_user_id
        await self.uow.flush()
        return invitation, token
