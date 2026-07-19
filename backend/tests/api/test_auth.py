import uuid

import pytest
from httpx import AsyncClient

from app.core.context import UserRole
from app.utils.security import create_access_token
from tests.factories import make_tenant, make_user


@pytest.mark.integration
async def test_register_new_tenant_and_admin(async_client: AsyncClient, db_session):
    payload = {
        "tenant_name": "API Register Corp",
        "email": "apireg@test.com",
        "password": "strongPassword123",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "apireg@test.com"
    assert data["role"] == "ADMIN"


@pytest.mark.integration
async def test_login_returns_jwt_tokens(async_client: AsyncClient, db_session):
    tenant = make_tenant(slug="api-login")
    db_session.add(tenant)
    await db_session.commit()

    user = make_user(
        tenant_id=tenant.id, email="apilogin@test.com", password="password123"
    )
    db_session.add(user)
    await db_session.commit()

    payload = {"email": "apilogin@test.com", "password": "password123"}
    headers = {"X-Tenant-Slug": "api-login"}
    response = await async_client.post(
        "/api/v1/auth/login", json=payload, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
