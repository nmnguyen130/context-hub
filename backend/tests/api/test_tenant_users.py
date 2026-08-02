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
async def test_get_current_tenant_details(async_client: AsyncClient, db_session):
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
async def test_patch_tenant_admin_only(async_client: AsyncClient, db_session):
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


@pytest.mark.integration
async def test_role_update_rejected_for_members(async_client: AsyncClient, db_session):
    tenant = make_tenant()
    db_session.add(tenant)
    await db_session.commit()

    user_member = make_user(
        tenant_id=tenant.id, email="member@test.com", role=UserRole.MEMBER
    )
    user_target = make_user(
        tenant_id=tenant.id, email="target@test.com", role=UserRole.VIEWER
    )
    db_session.add(user_member)
    db_session.add(user_target)
    await db_session.commit()

    # Members cannot update roles (returns 403)
    headers = get_headers(user_member.id, tenant.id, UserRole.MEMBER)
    payload = {"role": "ADMIN"}
    response = await async_client.patch(
        f"/api/v1/auth/users/{user_target.id}/role", json=payload, headers=headers
    )
    assert response.status_code == 403


@pytest.mark.integration
async def test_api_tenant_isolation_list(async_client: AsyncClient, db_session):
    """Verify that listing users from Tenant A does not reveal users from Tenant B."""
    tenant_a = make_tenant(slug="tenant-a")
    tenant_b = make_tenant(slug="tenant-b")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.commit()

    user_a = make_user(
        tenant_id=tenant_a.id, email="usera@tenant-a.com", role=UserRole.ADMIN
    )
    user_b = make_user(
        tenant_id=tenant_b.id, email="userb@tenant-b.com", role=UserRole.ADMIN
    )
    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.commit()

    headers = get_headers(user_a.id, tenant_a.id, UserRole.ADMIN)
    response = await async_client.get("/api/v1/auth/users", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Tenant A should only see their own user
    assert len(data["items"]) == 1
    emails = [item["email"] for item in data["items"]]
    assert "usera@tenant-a.com" in emails
    assert "userb@tenant-b.com" not in emails


@pytest.mark.integration
async def test_api_tenant_isolation_update(async_client: AsyncClient, db_session):
    """Verify that Tenant A cannot modify or even access Tenant B's users (returns 404)."""
    tenant_a = make_tenant(slug="tenant-a")
    tenant_b = make_tenant(slug="tenant-b")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.commit()

    user_a = make_user(
        tenant_id=tenant_a.id, email="admina@tenant-a.com", role=UserRole.ADMIN
    )
    user_b_member = make_user(
        tenant_id=tenant_b.id, email="memberb@tenant-b.com", role=UserRole.MEMBER
    )
    db_session.add(user_a)
    db_session.add(user_b_member)
    await db_session.commit()

    # Tenant A attempts to update role of Tenant B's member
    headers = get_headers(user_a.id, tenant_a.id, UserRole.ADMIN)
    payload = {"role": "ADMIN"}

    response = await async_client.patch(
        f"/api/v1/auth/users/{user_b_member.id}/role", json=payload, headers=headers
    )

    # Should be 404 because RLS makes user_b invisible to Tenant A's connection
    assert response.status_code == 404
