import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.modules.auth.models import User
from app.modules.tenant.models import Tenant


@pytest.mark.asyncio
async def test_multi_tenant_isolation(client: AsyncClient, db: AsyncSession):
    # 1. Register Tenant A
    reg_a = {
        "email": "admin@tenant-a.com",
        "password": "password123",
        "first_name": "Admin",
        "last_name": "A",
        "tenant_name": "Tenant A Org",
    }
    resp_a = await client.post("/api/v1/auth/register", json=reg_a)
    assert resp_a.status_code == 201
    tenant_a_id = resp_a.json()["tenant_id"]

    # 2. Register Tenant B
    reg_b = {
        "email": "admin@tenant-b.com",
        "password": "password123",
        "first_name": "Admin",
        "last_name": "B",
        "tenant_name": "Tenant B Org",
    }
    resp_b = await client.post("/api/v1/auth/register", json=reg_b)
    assert resp_b.status_code == 201
    tenant_b_id = resp_b.json()["tenant_id"]

    # 3. Log in as Tenant A
    login_a_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@tenant-a.com",
            "password": "password123",
            "tenant_slug": "tenant-a-org",
        },
    )
    assert login_a_resp.status_code == 200
    token_a = login_a_resp.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 4. Log in as Tenant B
    login_b_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@tenant-b.com",
            "password": "password123",
            "tenant_slug": "tenant-b-org",
        },
    )
    assert login_b_resp.status_code == 200
    token_b = login_b_resp.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 5. Verify Tenant A admin cannot fetch users from Tenant B
    # Get Tenant B admin user ID
    user_b_stmt = (
        select(User)
        .where(User.email == "admin@tenant-b.com")
        .execution_options(skip_tenant_filter=True)
    )
    user_b = (await db.execute(user_b_stmt)).scalar_one()

    # Try to access Tenant B user using Tenant A's token
    hack_resp = await client.get(f"/api/v1/users/{user_b.id}", headers=headers_a)
    # The default tenant loader criteria handles filtering, meaning Tenant A's query
    # will result in user not found (404) or forbidden since it cannot see Tenant B's row.
    assert hack_resp.status_code == 404

    # 6. Verify Tenant A admin lists users and only sees Tenant A users
    list_a_resp = await client.get("/api/v1/users", headers=headers_a)
    assert list_a_resp.status_code == 200
    list_a_data = list_a_resp.json()
    assert list_a_data["total"] == 1
    assert list_a_data["users"][0]["email"] == "admin@tenant-a.com"

    # Verify Tenant B admin lists users and only sees Tenant B users
    list_b_resp = await client.get("/api/v1/users", headers=headers_b)
    assert list_b_resp.status_code == 200
    list_b_data = list_b_resp.json()
    assert list_b_data["total"] == 1
    assert list_b_data["users"][0]["email"] == "admin@tenant-b.com"
