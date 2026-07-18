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
async def test_list_users(async_client: AsyncClient, db_session):
    tenant = make_tenant()
    db_session.add(tenant)
    await db_session.commit()

    user_1 = make_user(tenant_id=tenant.id, email="u1@test.com", role=UserRole.ADMIN)
    user_2 = make_user(tenant_id=tenant.id, email="u2@test.com", role=UserRole.MEMBER)
    db_session.add(user_1)
    db_session.add(user_2)
    await db_session.commit()

    headers = get_headers(user_1.id, tenant.id, UserRole.ADMIN)
    response = await async_client.get("/api/v1/auth/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    emails = [item["email"] for item in data["items"]]
    assert "u1@test.com" in emails
    assert "u2@test.com" in emails


@pytest.mark.integration
async def test_role_update_403_for_member(async_client: AsyncClient, db_session):
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

    # Members cannot update roles
    headers = get_headers(user_member.id, tenant.id, UserRole.MEMBER)
    payload = {"role": "ADMIN"}
    response = await async_client.patch(
        f"/api/v1/auth/users/{user_target.id}/role", json=payload, headers=headers
    )
    assert response.status_code == 403
