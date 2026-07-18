import uuid

import pytest

from app.core.exceptions import ServiceError
from app.modules.auth.models import InvitationStatus
from app.modules.auth.schemas import InvitationCreate
from app.modules.auth.services.invitation_service import InvitationService
from tests.factories import make_invitation, make_tenant, make_user


@pytest.mark.integration
async def test_create_and_list_invitations(uow):
    service = InvitationService(uow)
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    user = make_user(tenant_id=tenant.id)
    uow.session.add(user)
    await uow.flush()

    data = InvitationCreate(email="invite@test.com")
    invite, token = await service.create_invitation(
        tenant_id=tenant.id,
        invited_by=user.id,
        data=data,
    )
    assert invite.email == "invite@test.com"
    assert token is not None

    items, total = await service.list_invitations(tenant_id=tenant.id)
    assert total == 1
    assert items[0].email == "invite@test.com"


@pytest.mark.integration
async def test_revoke_invitation(uow):
    service = InvitationService(uow)
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    invite = make_invitation(tenant_id=tenant.id, email="revoke@test.com")
    uow.session.add(invite)
    await uow.flush()

    await service.revoke_invitation(tenant_id=tenant.id, invitation_id=invite.id)
    assert invite.status == InvitationStatus.REVOKED
