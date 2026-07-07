import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import InvitationStatus, UserRole
from app.core.exceptions import ServiceError
from app.core.security import hash_token
from app.modules.audit.service import AuditService
from app.modules.auth.models import Invitation, User
from app.modules.auth.schemas import InviteCreateRequest


from fastapi import Depends
from app.api.deps import get_db


class InvitationService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create(
        self,
        tenant_id: UUID,
        invited_by: UUID,
        data: InviteCreateRequest,
        expires_in_days: int = 7,
    ) -> tuple[Invitation, str]:
        """Creates an invitation, generates invite JWT, hashes and saves to DB."""
        # 1. Verify user does not already exist in tenant
        user_stmt = (
            select(User)
            .where(User.email == data.email, User.tenant_id == tenant_id)
            .execution_options(skip_tenant_filter=True)
        )
        existing_user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if existing_user:
            raise ServiceError(
                "User with this email is already a member of this tenant",
                status_code=409,
            )

        # 2. Check if a PENDING invitation already exists for this email
        pending_stmt = (
            select(Invitation)
            .where(
                Invitation.email == data.email,
                Invitation.tenant_id == tenant_id,
                Invitation.status == InvitationStatus.PENDING,
            )
            .execution_options(skip_tenant_filter=True)
        )
        existing_invite = (await self.db.execute(pending_stmt)).scalar_one_or_none()
        if existing_invite:
            # If expired, we let it proceed or raise. Better to raise, so admin can call "resend" instead.
            if existing_invite.expires_at.replace(tzinfo=UTC) >= datetime.now(UTC):
                raise ServiceError(
                    "A pending invitation already exists for this email",
                    status_code=409,
                )
            else:
                # Mark old one expired
                existing_invite.status = InvitationStatus.EXPIRED
                self.db.add(existing_invite)

        # 3. Insert skeleton Invitation to get the ID
        invite_id = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        # 4. Generate JWT
        payload = {
            "invite_id": str(invite_id),
            "tenant_id": str(tenant_id),
            "email": data.email,
            "role": data.role,
            "exp": expires_at,
        }
        token_str = jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )
        token_hash = hash_token(token_str)

        # 5. Save Invitation
        invitation = Invitation(
            id=invite_id,
            tenant_id=tenant_id,
            invited_by=invited_by,
            email=data.email,
            role=data.role,
            status=InvitationStatus.PENDING,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(invitation)

        # 6. Log Audit
        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=invited_by,
            action="INVITATION_CREATE",
            resource_type="Invitation",
            resource_id=invitation.id,
        )

        await self.db.flush()
        return invitation, token_str

    async def list_invitations(
        self,
        tenant_id: UUID,
        status: InvitationStatus | None = None,
    ) -> list[Invitation]:
        """Lists invitations for the current tenant, optionally filtered by status."""
        query = select(Invitation).where(Invitation.tenant_id == tenant_id)
        if status:
            query = query.where(Invitation.status == status)

        return list((await self.db.execute(query)).scalars().all())

    async def get_by_id(self, tenant_id: UUID, invitation_id: UUID) -> Invitation:
        stmt = select(Invitation).where(
            Invitation.id == invitation_id, Invitation.tenant_id == tenant_id
        )
        invite = (await self.db.execute(stmt)).scalar_one_or_none()
        if not invite:
            raise ServiceError("Invitation not found", status_code=404)
        return invite

    async def revoke(
        self, tenant_id: UUID, invitation_id: UUID, revoked_by: UUID | None = None
    ) -> None:
        """Revokes a pending invitation."""
        invitation = await self.get_by_id(tenant_id, invitation_id)

        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError(
                f"Cannot revoke an invitation that is {invitation.status.lower()}",
                status_code=400,
            )

        invitation.status = InvitationStatus.REVOKED
        self.db.add(invitation)

        # Log Audit
        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=revoked_by,
            action="INVITATION_REVOKE",
            resource_type="Invitation",
            resource_id=invitation.id,
        )
        await self.db.flush()

    async def resend(
        self,
        tenant_id: UUID,
        invitation_id: UUID,
        resending_user_id: UUID,
        expires_in_days: int = 7,
    ) -> tuple[Invitation, str]:
        """Revokes the old invitation token and creates a new one with a fresh expiry."""
        invitation = await self.get_by_id(tenant_id, invitation_id)

        if invitation.status not in (
            InvitationStatus.PENDING,
            InvitationStatus.EXPIRED,
        ):
            raise ServiceError(
                f"Cannot resend an invitation that is {invitation.status.lower()}",
                status_code=400,
            )

        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        payload = {
            "invite_id": str(invitation.id),
            "tenant_id": str(tenant_id),
            "email": invitation.email,
            "role": invitation.role,
            "exp": expires_at,
        }
        token_str = jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )
        token_hash = hash_token(token_str)

        invitation.token_hash = token_hash
        invitation.expires_at = expires_at
        invitation.status = InvitationStatus.PENDING
        invitation.invited_by = resending_user_id

        self.db.add(invitation)

        # Log Audit
        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=resending_user_id,
            action="INVITATION_RESEND",
            resource_type="Invitation",
            resource_id=invitation.id,
        )
        await self.db.flush()
        return invitation, token_str
