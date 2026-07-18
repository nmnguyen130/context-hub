import uuid

import pytest

from app.core.context import UserRole
from app.core.exceptions import ServiceError
from app.modules.auth.schemas import ChangePasswordRequest, UserUpdate
from app.modules.auth.services.user_service import UserService
from tests.factories import make_tenant, make_user


@pytest.mark.integration
async def test_cannot_demote_last_admin(uow):
    service = UserService(uow)
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    admin = make_user(tenant_id=tenant.id, email="admin@test.com", role=UserRole.ADMIN)
    uow.session.add(admin)
    await uow.flush()

    data = UserUpdate(role=UserRole.MEMBER)
    # Demoting the only active admin should fail
    with pytest.raises(ServiceError) as exc_info:
        await service.update_role(
            tenant_id=tenant.id,
            target_user_id=admin.id,
            data=data,
            acting_user_id=uuid.uuid4(),  # Someone else acting
        )
    assert exc_info.value.status_code == 400


@pytest.mark.integration
async def test_cannot_deactivate_self(uow):
    service = UserService(uow)
    tenant = make_tenant()
    uow.session.add(tenant)
    await uow.flush()

    admin = make_user(tenant_id=tenant.id, email="admin@test.com", role=UserRole.ADMIN)
    uow.session.add(admin)
    await uow.flush()

    with pytest.raises(ServiceError) as exc_info:
        await service.deactivate(
            tenant_id=tenant.id,
            user_id=admin.id,
            acting_user_id=admin.id,
        )
    assert exc_info.value.status_code == 400
