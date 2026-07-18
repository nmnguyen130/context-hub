import uuid

import pytest
from httpx import AsyncClient

from app.core.context import UserRole
from app.utils.security import create_access_token
from tests.factories import make_tenant, make_user


def get_headers(user_id: uuid.UUID, tenant_id: uuid.UUID, role: UserRole) -> dict:
    token = create_access_token(user_id, tenant_id, role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
async def test_get_current_tenant(async_client: AsyncClient, db_session):
    tenant = make_tenant(name="Target Tenant")
    db_session.add(tenant)
    await db_session.commit()

    user = make_user(tenant_id=tenant.id, email="tenant-get@test.com")
    db_session.add(user)
    await db_session.commit()

    headers = get_headers(user.id, tenant.id, UserRole.MEMBER)
    response = await async_client.get("/api/v1/tenant", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Target Tenant"
    assert data["id"] == str(tenant.id)


@pytest.mark.integration
async def test_patch_tenant(async_client: AsyncClient, db_session):
    tenant = make_tenant(name="Old Name")
    db_session.add(tenant)
    await db_session.commit()

    user = make_user(
        tenant_id=tenant.id, email="tenant-patch@test.com", role=UserRole.ADMIN
    )
    db_session.add(user)
    await db_session.commit()

    headers = get_headers(user.id, tenant.id, UserRole.ADMIN)
    payload = {"name": "New Name", "settings": {"branding": "blue"}}
    response = await async_client.patch("/api/v1/tenant", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["settings"] == {"branding": "blue"}
