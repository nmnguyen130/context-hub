import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import InvitationStatus, UserRole
from app.modules.auth.models import Invitation, RefreshToken, User
from app.modules.tenant.models import Tenant


@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient, db: AsyncSession):
    # 1. Register a new tenant
    reg_data = {
        "email": "admin@acme.com",
        "password": "supersecurepassword123",
        "first_name": "Acme",
        "last_name": "Admin",
        "tenant_name": "Acme Corporation",
    }
    response = await client.post("/api/v1/auth/register", json=reg_data)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["email"] == "admin@acme.com"
    assert res_data["role"] == "ADMIN"
    tenant_id = res_data["tenant_id"]

    # Verify tenant was created in DB with correct slug
    tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = (await db.execute(tenant_stmt)).scalar_one()
    assert tenant.slug == "acme-corporation"

    # 2. Login with correct slug
    login_data = {
        "email": "admin@acme.com",
        "password": "supersecurepassword123",
        "tenant_slug": "acme-corporation",
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    login_res = response.json()
    assert "access_token" in login_res
    assert "refresh_token" in login_res
    assert login_res["token_type"] == "bearer"

    access_token = login_res["access_token"]
    refresh_token = login_res["refresh_token"]

    # 3. Access /auth/me with token
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "admin@acme.com"

    # 4. Refresh token rotation
    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    refresh_res = refresh_resp.json()
    assert "access_token" in refresh_res
    assert "refresh_token" in refresh_res

    new_access_token = refresh_res["access_token"]
    new_refresh_token = refresh_res["refresh_token"]

    # Verify old refresh token is revoked in DB
    tokens_stmt = select(RefreshToken).execution_options(skip_tenant_filter=True)
    all_tokens = (await db.execute(tokens_stmt)).scalars().all()
    assert len(all_tokens) == 2
    # One is revoked (the original one), one is active
    revoked_tokens = [t for t in all_tokens if t.is_revoked]
    active_tokens = [t for t in all_tokens if not t.is_revoked]
    assert len(revoked_tokens) == 1
    assert len(active_tokens) == 1

    # 5. Theft detection: try to reuse the OLD refresh token
    theft_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert theft_resp.status_code == 401
    assert "reuse detected" in theft_resp.json()["detail"].lower()

    # Verify all tokens are now revoked for this user
    db.expire_all()
    all_tokens_after = (await db.execute(tokens_stmt)).scalars().all()
    assert all(t.is_revoked for t in all_tokens_after)

    # Re-login to get clean session
    login_response = await client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    # 6. Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_resp.status_code == 204

    # Verify that refresh token is marked revoked
    db.expire_all()
    logout_token_stmt = (
        select(RefreshToken)
        .where(RefreshToken.revoked_at.isnot(None))
        .execution_options(skip_tenant_filter=True)
    )
    revoked_count = len((await db.execute(logout_token_stmt)).scalars().all())
    # Should have old ones plus the logged out one
    assert revoked_count >= 1


@pytest.mark.asyncio
async def test_invitation_lifecycle(client: AsyncClient, db: AsyncSession):
    # 1. Setup admin and organization
    reg_data = {
        "email": "admin@globex.com",
        "password": "password123",
        "first_name": "Globex",
        "last_name": "Boss",
        "tenant_name": "Globex Corp",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_data)
    assert reg_resp.status_code == 201
    admin_token = (
        await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@globex.com",
                "password": "password123",
                "tenant_slug": "globex-corp",
            },
        )
    ).json()["access_token"]

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Invite a new member
    invite_data = {
        "email": "worker@globex.com",
        "role": "MEMBER",
    }
    invite_resp = await client.post(
        "/api/v1/auth/invitations", json=invite_data, headers=headers
    )
    assert invite_resp.status_code == 201
    invite_res = invite_resp.json()
    assert "invite_token" in invite_res
    invite_token = invite_res["invite_token"]
    invitation_id = invite_res["invitation_id"]

    # Verify DB contains pending invitation
    invite_stmt = (
        select(Invitation)
        .where(Invitation.id == invitation_id)
        .execution_options(skip_tenant_filter=True)
    )
    invitation = (await db.execute(invite_stmt)).scalar_one()
    assert invitation.status == InvitationStatus.PENDING

    # 3. Accept invitation
    join_data = {
        "email": "worker@globex.com",
        "password": "workerpassword123",
        "first_name": "Globex",
        "last_name": "Worker",
        "invite_token": invite_token,
    }
    join_resp = await client.post("/api/v1/auth/invitations/accept", json=join_data)
    assert join_resp.status_code == 201

    # Verify invitation marked accepted and user is created
    db.expire_all()
    invitation = (await db.execute(invite_stmt)).scalar_one()
    assert invitation.status == InvitationStatus.ACCEPTED

    user_stmt = (
        select(User)
        .where(User.email == "worker@globex.com")
        .execution_options(skip_tenant_filter=True)
    )
    worker_user = (await db.execute(user_stmt)).scalar_one()
    assert worker_user.role == UserRole.MEMBER


@pytest.mark.asyncio
async def test_admin_user_management(client: AsyncClient, db: AsyncSession):
    # 1. Setup organization and admin
    reg_data = {
        "email": "owner@company.com",
        "password": "password123",
        "first_name": "Company",
        "last_name": "Owner",
        "tenant_name": "Big Company",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_data)
    assert reg_resp.status_code == 201
    tenant_id = reg_resp.json()["tenant_id"]

    admin_token = (
        await client.post(
            "/api/v1/auth/login",
            json={
                "email": "owner@company.com",
                "password": "password123",
                "tenant_slug": "big-company",
            },
        )
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Add second user via manual DB insertion (simulate accepted invite)
    other_user = User(
        tenant_id=tenant_id,
        email="employee@company.com",
        password_hash="dummyhash",
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(other_user)
    await db.commit()
    await db.refresh(other_user)

    # 3. Admin lists users
    list_resp = await client.get("/api/v1/users", headers=headers)
    assert list_resp.status_code == 200
    list_res = list_resp.json()
    assert list_res["total"] == 2

    # 4. Admin changes user role
    role_change_resp = await client.patch(
        f"/api/v1/users/{other_user.id}/role",
        json={"role": "VIEWER"},
        headers=headers,
    )
    assert role_change_resp.status_code == 200
    assert role_change_resp.json()["role"] == "VIEWER"

    # 5. Admin deactivates user
    deactivate_resp = await client.post(
        f"/api/v1/users/{other_user.id}/deactivate",
        headers=headers,
    )
    assert deactivate_resp.status_code == 204

    # Verify user is deactivated in DB
    db.expire_all()
    user_stmt = (
        select(User)
        .where(User.id == other_user.id)
        .execution_options(skip_tenant_filter=True)
    )
    updated_user = (await db.execute(user_stmt)).scalar_one()
    assert not updated_user.is_active
