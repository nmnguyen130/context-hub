from datetime import UTC, datetime
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import InvitationStatus, UserRole
from app.core.exceptions import ServiceError
from app.core.security import hash_password, hash_token
from app.modules.audit.service import AuditService
from app.modules.auth.models import Invitation, User
from app.modules.auth.schemas import JoinRequest, RegisterRequest
from app.modules.tenant.models import Tenant
from app.modules.tenant.services.tenant_service import TenantService


from fastapi import Depends
from app.api.deps import get_db


class RegistrationService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def register(self, data: RegisterRequest) -> tuple[User, Tenant]:
        """Registers a new Tenant and its initial Administrator user."""
        # 1. Generate slug
        slug = TenantService.generate_slug(data.tenant_name)

        # 2. Verify global slug uniqueness
        slug_stmt = (
            select(Tenant)
            .where(Tenant.slug == slug)
            .execution_options(skip_tenant_filter=True)
        )
        existing_tenant = (await self.db.execute(slug_stmt)).scalar_one_or_none()
        if existing_tenant:
            raise ServiceError(
                "Tenant with this name or slug already exists", status_code=409
            )

        # 3. Check if email is already registered in any active tenant with role ADMIN?
        # Actually, since email unique constraint is (email, tenant_id),
        # this is a new tenant, so it's guaranteed unique in this new tenant.
        # But let's check globally if we want to enforce unique email globally or just let it go.
        # The plan says "per-tenant email uniqueness", so we only check uniqueness inside the tenant.
        # Since the tenant is new, it has no other users. So it's unique!

        # 4. Create Tenant
        tenant = Tenant(
            name=data.tenant_name,
            slug=slug,
            plan_tier="STARTER",
            settings={},
        )
        self.db.add(tenant)
        await self.db.flush()  # Populate tenant.id

        # 5. Create Administrator User
        user = User(
            tenant_id=tenant.id,
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        # 6. Audit Logging
        await AuditService(self.db).log(
            tenant_id=tenant.id,
            user_id=user.id,
            action="USER_REGISTER",
            resource_type="Tenant",
            resource_id=tenant.id,
        )

        return user, tenant

    async def join_via_invitation(self, data: JoinRequest) -> User:
        """Registers a new user into an existing Tenant using a signed invitation token."""
        # 1. Decode token to extract payload
        try:
            payload = jwt.decode(
                data.invite_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            invite_id = UUID(payload["invite_id"])
            tenant_id = UUID(payload["tenant_id"])
            invite_email = payload["email"]
        except Exception:
            raise ServiceError("Invalid or expired invitation token", status_code=400)

        # Verify email matches invitation payload
        if data.email != invite_email:
            raise ServiceError(
                "Email address does not match invitation", status_code=400
            )

        # 2. Look up invitation record using hash of token
        token_hash = hash_token(data.invite_token)
        invite_stmt = (
            select(Invitation)
            .where(Invitation.id == invite_id, Invitation.token_hash == token_hash)
            .execution_options(skip_tenant_filter=True)
        )
        invitation = (await self.db.execute(invite_stmt)).scalar_one_or_none()

        if not invitation:
            raise ServiceError(
                "Invitation not found or token modified", status_code=404
            )

        if invitation.status != InvitationStatus.PENDING:
            raise ServiceError(
                f"Invitation has already been {invitation.status.lower()}",
                status_code=400,
            )

        if invitation.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            invitation.status = InvitationStatus.EXPIRED
            self.db.add(invitation)
            await self.db.flush()
            raise ServiceError("Invitation token has expired", status_code=400)

        # 3. Verify user does not already exist in tenant
        user_stmt = (
            select(User)
            .where(User.email == data.email, User.tenant_id == tenant_id)
            .execution_options(skip_tenant_filter=True)
        )
        existing_user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if existing_user:
            # Mark invitation as accepted if they already joined somehow,
            # but raising error is safer.
            raise ServiceError(
                "Email is already registered in this organization", status_code=409
            )

        # 4. Create the User
        user = User(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=invitation.role,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        # 5. Mark invitation accepted
        invitation.status = InvitationStatus.ACCEPTED
        self.db.add(invitation)

        # 6. Audit Logging
        await AuditService(self.db).log(
            tenant_id=tenant_id,
            user_id=user.id,
            action="USER_JOIN",
            resource_type="Invitation",
            resource_id=invitation.id,
        )

        return user
