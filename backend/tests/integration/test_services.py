import uuid

import pytest

from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.modules.auth.models import InvitationStatus
from app.modules.auth.schemas import InvitationCreate, UserUpdate
from app.modules.auth.services.invitation_service import InvitationService
from app.modules.auth.services.user_service import UserService
from tests.factories import make_invitation, make_tenant, make_user


@pytest.mark.integration
async def test_user_service_cannot_demote_last_admin(uow, make_tenant_uow):
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    admin = make_user(tenant_id=tenant.id, email="admin@test.com", role=UserRole.ADMIN)
    uow.session.add(admin)
    await uow.commit()

    # Access as Tenant A
    async with make_tenant_uow(tenant.id) as tenant_uow:
        service = UserService(tenant_uow)
        data = UserUpdate(role=UserRole.MEMBER)

        # Demoting the last active administrator must trigger a 400 Bad Request
        with pytest.raises(ServiceError) as exc_info:
            await service.update_role(
                target_user_id=admin.id,
                data=data,
                acting_user_id=uuid.uuid4(),
                acting_user_role=UserRole.SUPER_ADMIN,
            )
        assert exc_info.value.status_code == 400


@pytest.mark.integration
async def test_user_service_cannot_deactivate_self(uow, make_tenant_uow):
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    admin = make_user(tenant_id=tenant.id, email="admin@test.com", role=UserRole.ADMIN)
    uow.session.add(admin)
    await uow.commit()

    # Access as Tenant A
    async with make_tenant_uow(tenant.id) as tenant_uow:
        service = UserService(tenant_uow)

        # Activating user cannot deactivate self
        with pytest.raises(ServiceError) as exc_info:
            await service.deactivate(
                user_id=admin.id,
                acting_user_id=admin.id,
                acting_user_role=UserRole.ADMIN,
            )
        assert exc_info.value.status_code == 400


@pytest.mark.integration
async def test_invitation_service_flow(uow, make_tenant_uow):
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    user = make_user(tenant_id=tenant.id)
    uow.session.add(user)
    await uow.commit()

    # Scoped execution for Invitation creation/listing/revoking
    async with make_tenant_uow(tenant.id) as tenant_uow:
        service = InvitationService(tenant_uow)
        data = InvitationCreate(email="invite@test.com")

        invite, token = await service.create_invitation(
            tenant_id=tenant.id,
            invited_by=user.id,
            data=data,
            acting_user_role=UserRole.ADMIN,
        )
        assert invite.email == "invite@test.com"
        assert token is not None

        # Verify listing works
        items, next_cursor, has_more = await service.list_invitations(
            tenant_id=tenant.id
        )
        assert len(items) == 1
        assert items[0].email == "invite@test.com"

        # Revoke invitation
        await service.revoke_invitation(invitation_id=invite.id)
        await tenant_uow.flush()
        assert invite.status == InvitationStatus.REVOKED
