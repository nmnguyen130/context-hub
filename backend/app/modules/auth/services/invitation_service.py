import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy import func, select

from app.core.config import settings
from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.core.uow import UnitOfWork
from app.modules.auth.models import Invitation, InvitationStatus, User
from app.modules.auth.schemas import InvitationCreate
from app.utils.security import hash_token


class InvitationService:
    """Service to manage user invitations within a tenant."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

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
            "role": role.value,
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    async def create_invitation(
        self,
        tenant_id: UUID,
        invited_by: UUID,
        data: InvitationCreate,
        acting_user_role: UserRole,
        expires_in_days: int = 7,
    ) -> tuple[Invitation, str]:
        """Create a new invitation for a user to join a tenant organization."""
        # Enforce target role limit: acting user cannot invite a user with higher authority than their own
        if data.role.priority > acting_user_role.priority:
            raise ServiceError("Cannot invite a user with higher authority than your own", status_code=403)

        # 1. Assert user doesn't already exist in the organization
        existing_user = await self.uow.session.scalar(
            select(User).where(
                User.email == data.email.strip().lower(),
                User.tenant_id == tenant_id,
            )
        )
        if existing_user:
            raise ServiceError("User with this email is already a member", status_code=409)

        # 2. Assert no other active pending invitation exists
        pending = await self.uow.session.scalar(
            select(Invitation).where(
                Invitation.email == data.email.strip().lower(),
                Invitation.tenant_id == tenant_id,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        if pending:
            if pending.expires_at >= datetime.now(UTC):
                raise ServiceError("A pending invitation already exists", status_code=409)
            # Auto-expire outdated pending invitation
            pending.status = InvitationStatus.EXPIRED
            await self.uow.flush()

        invitation_id = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        token = self._create_invitation_token(
            invitation_id, tenant_id, data.email, data.role, expires_at
        )

        invitation = Invitation(
            id=invitation_id,
            tenant_id=tenant_id,
            invited_by=invited_by,
            email=data.email.strip().lower(),
            role=data.role,
            status=InvitationStatus.PENDING,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )
        self.uow.session.add(invitation)
        await self.uow.flush()
        return invitation, token

    async def list_invitations(
        self,
        tenant_id: UUID,
        status: InvitationStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Invitation], int]:
        """List invitations for a tenant, optionally filtered by status, with pagination."""
        stmt = select(Invitation).where(Invitation.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Invitation.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.uow.session.scalar(count_stmt) or 0

        paginated = stmt.offset(skip).limit(limit)
        result = await self.uow.session.scalars(paginated)
        return list(result.all()), total

    async def get_invitation_by_id(
        self, tenant_id: UUID, invitation_id: UUID
    ) -> Invitation:
        """Retrieve an invitation by ID, verifying tenant scoping."""
        invitation = await self.uow.session.get(Invitation, invitation_id)
        if not invitation or invitation.tenant_id != tenant_id:
            raise ServiceError("Invitation not found", status_code=404)
        return invitation

    async def revoke_invitation(self, tenant_id: UUID, invitation_id: UUID) -> None:
        """Revoke a pending invitation."""
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
        """Regenerate a fresh token and extend expiry for an existing invitation."""
        invitation = await self.get_invitation_by_id(tenant_id, invitation_id)
        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError("Cannot resend this invitation", status_code=400)

        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        token = self._create_invitation_token(
            invitation.id,
            tenant_id,
            invitation.email,
            invitation.role,
            expires_at,
        )
        invitation.token_hash = hash_token(token)
        invitation.expires_at = expires_at
        invitation.invited_by = resending_user_id

        await self.uow.flush()
        return invitation, token
