import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_invite_token


@pytest.mark.asyncio
async def test_auth_flows(client: AsyncClient, db: AsyncSession):
    # 1. Admin Registration (Creates new tenant & user)
    reg_payload = {
        "email": "admin@acme.com",
        "password": "securepassword123",
        "first_name": "John",
        "last_name": "Doe",
        "tenant_name": "Acme Corp",
    }

    response = await client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["email"] == "admin@acme.com"
    assert res_data["role"] == "ADMIN"
    tenant_id = res_data["tenant_id"]
    assert tenant_id is not None

    # 2. Duplicate registration attempt (should fail 400)
    response = await client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

    # 3. Employee Join Registration via invite token
    invite_email = "employee@acme.com"
    invite_token = create_invite_token(
        tenant_id=tenant_id, email=invite_email, role="MEMBER"
    )

    join_payload = {
        "email": invite_email,
        "password": "employeepassword123",
        "first_name": "Alice",
        "last_name": "Smith",
        "invite_token": invite_token,
    }

    response = await client.post("/api/v1/auth/register/join", json=join_payload)
    assert response.status_code == 201
    join_data = response.json()
    assert join_data["email"] == invite_email
    assert join_data["role"] == "MEMBER"
    assert join_data["tenant_id"] == tenant_id

    # 4. Mismatched email join attempt (should fail 400)
    mismatched_payload = join_payload.copy()
    mismatched_payload["email"] = "hacker@acme.com"
    response = await client.post("/api/v1/auth/register/join", json=mismatched_payload)
    assert response.status_code == 400

    # 5. Invalid invite token join attempt (should fail 400)
    invalid_payload = join_payload.copy()
    invalid_payload["invite_token"] = "invalid-token"
    response = await client.post("/api/v1/auth/register/join", json=invalid_payload)
    assert response.status_code == 400

    # 6. JSON Login Admin
    login_payload = {"email": "admin@acme.com", "password": "securepassword123"}
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    login_data = response.json()
    assert "access_token" in login_data
    access_token = login_data["access_token"]

    # 7. Login with wrong password (should fail 401)
    wrong_login = login_payload.copy()
    wrong_login["password"] = "wrongpassword"
    response = await client.post("/api/v1/auth/login", json=wrong_login)
    assert response.status_code == 401

    # 9. GET /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["email"] == "admin@acme.com"
    assert me_data["tenant_id"] == tenant_id

    # 10. GET /auth/me without authorization (should fail 401)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
