import uuid

import pytest

from app.core.exceptions import ServiceError
from app.modules.tenant.schemas import TenantCreate, TenantUpdate
from app.modules.tenant.services.tenant_service import TenantService
from tests.factories import make_tenant


@pytest.mark.integration
async def test_create_tenant(uow):
    service = TenantService(uow)
    data = TenantCreate(name="Acme Corporation", slug="acme-corp")
    tenant = await service.create(data)
    assert tenant.id is not None
    assert tenant.name == "Acme Corporation"
    assert tenant.slug == "acme-corp"


@pytest.mark.integration
async def test_duplicate_slug_raises_409(uow):
    service = TenantService(uow)
    t1 = make_tenant(slug="dup-corp")
    uow.session.add(t1)
    await uow.flush()

    data = TenantCreate(name="Duplicate Corp", slug="dup-corp")
    with pytest.raises(ServiceError) as exc_info:
        await service.create(data)
    assert exc_info.value.status_code == 409


@pytest.mark.integration
async def test_update_tenant_blocks_slug(uow):
    service = TenantService(uow)
    tenant = make_tenant(name="Before Update", slug="block-slug")
    uow.session.add(tenant)
    await uow.flush()

    data = TenantUpdate(name="After Update", settings={"theme": "dark"})
    updated = await service.update(tenant.id, data)
    assert updated.name == "After Update"
    assert updated.slug == "block-slug"
    assert updated.settings == {"theme": "dark"}


@pytest.mark.integration
async def test_soft_delete(uow):
    service = TenantService(uow)
    tenant = make_tenant(name="To Delete")
    uow.session.add(tenant)
    await uow.flush()

    await service.delete(tenant.id)
    retrieved = await service.get_by_id(tenant.id)
    assert retrieved.is_active is False
