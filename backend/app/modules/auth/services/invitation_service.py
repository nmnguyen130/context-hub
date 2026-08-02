import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.core.pagination import CursorParams, paginate_cursor
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
        """Create a new invitation for a user to join a tenant organization with a clean, single flow."""
        if data.role.priority > acting_user_role.priority:
            raise ServiceError.forbidden(
                "Cannot invite a user with higher authority than your own"
            )

        clean_email = data.email.strip().lower()

        user_exists = await self.uow.session.scalar(
            select(User.id).where(
                User.tenant_id == tenant_id,
                User.email == clean_email,
            )
        )
        if user_exists:
            raise ServiceError.conflict("User with this email is already a member")

        pending = await self.uow.session.scalar(
            select(Invitation).where(
                Invitation.tenant_id == tenant_id,
                Invitation.email == clean_email,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        if pending:
            if pending.expires_at >= datetime.now(UTC):
                raise ServiceError.conflict("A pending invitation already exists")
            pending.status = InvitationStatus.EXPIRED

        invitation_id = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        token = self._create_invitation_token(
            invitation_id, tenant_id, clean_email, data.role, expires_at
        )

        invitation = Invitation(
            id=invitation_id,
            tenant_id=tenant_id,
            invited_by=invited_by,
            email=clean_email,
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
        params: CursorParams | None = None,
    ) -> tuple[list[Invitation], str | None, bool]:
        """List invitations for a tenant with cursor pagination."""
        params = params or CursorParams()
        stmt = select(Invitation).where(Invitation.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Invitation.status == status)

        return await paginate_cursor(
            self.uow.session,
            stmt,
            params,
            sort_column=Invitation.created_at,
            id_column=Invitation.id,
        )

    async def get_invitation_by_id(self, invitation_id: UUID) -> Invitation:
        """Retrieve an invitation by ID."""
        invitation = await self.uow.session.get(Invitation, invitation_id)
        if not invitation:
            raise ServiceError.not_found("Invitation")
        return invitation

    async def revoke_invitation(self, invitation_id: UUID) -> None:
        """Revoke a pending invitation."""
        invitation = await self.get_invitation_by_id(invitation_id)
        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError.bad_request("Cannot revoke this invitation")

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
        invitation = await self.get_invitation_by_id(invitation_id)
        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError.bad_request("Cannot resend this invitation")

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
