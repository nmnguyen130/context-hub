import uuid
from datetime import UTC, datetime, timedelta

from app.core.context import UserRole
from app.modules.auth.models import Invitation, InvitationStatus, RefreshToken, User
from app.modules.tenant.models import PlanTier, Tenant
from app.utils.security import hash_password


def make_tenant(
    *,
    name: str = "Test Corp",
    slug: str | None = None,
    plan_tier: PlanTier = PlanTier.FREE,
    is_active: bool = True,
) -> Tenant:
    return Tenant(
        id=uuid.uuid4(),
        name=name,
        slug=slug or f"test-corp-{uuid.uuid4().hex[:6]}",
        plan_tier=plan_tier,
        is_active=is_active,
    )


def make_user(
    *,
    tenant_id: uuid.UUID,
    email: str = "user@test.com",
    password: str = "secureP@ss1",
    role: UserRole = UserRole.MEMBER,
    is_active: bool = True,
) -> User:
    return User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )


def make_invitation(
    *,
    tenant_id: uuid.UUID,
    invited_by: uuid.UUID | None = None,
    email: str = "invited@test.com",
    role: UserRole = UserRole.MEMBER,
    status: InvitationStatus = InvitationStatus.PENDING,
    token_hash: str = "some_token_hash",
    expires_at: datetime | None = None,
) -> Invitation:
    return Invitation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invited_by=invited_by,
        email=email,
        role=role,
        status=status,
        token_hash=token_hash,
        expires_at=expires_at or (datetime.now(UTC) + timedelta(days=7)),
    )


def make_refresh_token(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    token_hash: str = "some_refresh_hash",
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> RefreshToken:
    return RefreshToken(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at or (datetime.now(UTC) + timedelta(days=7)),
        revoked_at=revoked_at,
    )
