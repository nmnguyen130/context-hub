import uuid

import pytest

from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.modules.auth.schemas import InvitationAccept, RegisterRequest
from app.modules.auth.services.registration_service import RegistrationService
from app.utils.security import create_access_token, decode_token, hash_token
from tests.factories import make_invitation, make_tenant, make_user


@pytest.mark.integration
async def test_register_creates_tenant_and_admin(uow):
    service = RegistrationService(uow)
    data = RegisterRequest(
        tenant_name="Atomic Corp",
        email="admin@atomic.com",
        password="securePassword123",
    )
    user, tenant = await service.register(data)
    assert tenant.name == "Atomic Corp"
    assert tenant.slug == "atomic-corp"
    assert user.email == "admin@atomic.com"
    assert user.role == UserRole.ADMIN
    assert user.tenant_id == tenant.id


@pytest.mark.integration
async def test_register_duplicate_409(uow):
    service = RegistrationService(uow)
    existing = make_tenant(slug="taken-slug")
    uow.session.add(existing)
    await uow.flush()

    data = RegisterRequest(
        tenant_name="Taken Slug", email="admin@slug.com", password="securePassword123"
    )
    with pytest.raises(ServiceError) as exc_info:
        await service.register(data)
    assert exc_info.value.status_code == 409


@pytest.mark.integration
async def test_join_via_invitation(uow):
    service = RegistrationService(uow)
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    from app.modules.auth.services.invitation_service import InvitationService

    # We will generate a mock token and invitation manually
    invite_id = uuid.uuid4()
    # Build payload similar to InvitationService._create_invitation_token
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.core.config import settings

    expires_at = datetime.now(UTC) + timedelta(days=7)
    payload = {
        "invite_id": str(invite_id),
        "tenant_id": str(tenant.id),
        "email": "join@test.com",
        "role": UserRole.MEMBER.value,
        "exp": int(expires_at.timestamp()),
    }
    raw_token = jwt.encode(
        payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

    invitation = make_invitation(
        tenant_id=tenant.id,
        email="join@test.com",
        role=UserRole.MEMBER,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
    )
    invitation.id = invite_id
    uow.session.add(invitation)
    await uow.flush()

    data = InvitationAccept(
        invite_token=raw_token,
        email="join@test.com",
        password="password123",
    )
    user = await service.join_via_invitation(data)
    assert user.email == "join@test.com"
    assert user.role == UserRole.MEMBER
    assert user.tenant_id == tenant.id
