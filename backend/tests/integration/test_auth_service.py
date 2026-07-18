import uuid

import pytest

from app.core.exceptions import ServiceError
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.services.auth_service import AuthService
from tests.factories import make_refresh_token, make_tenant, make_user


@pytest.mark.integration
async def test_login_success(uow):
    service = AuthService(uow)
    tenant = make_tenant(slug="login-test")
    uow.session.add(tenant)
    await uow.flush()

    user = make_user(
        tenant_id=tenant.id, email="login@test.com", password="correct_password"
    )
    uow.session.add(user)
    await uow.flush()

    data = LoginRequest(email="login@test.com", password="correct_password")
    tokens = await service.login(data, tenant_slug="login-test")
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None


@pytest.mark.integration
async def test_login_wrong_password_401(uow):
    service = AuthService(uow)
    tenant = make_tenant(slug="login-fail")
    uow.session.add(tenant)
    await uow.flush()

    user = make_user(
        tenant_id=tenant.id, email="fail@test.com", password="correct_password"
    )
    uow.session.add(user)
    await uow.flush()

    data = LoginRequest(email="fail@test.com", password="wrong_password")
    with pytest.raises(ServiceError) as exc_info:
        await service.login(data, tenant_slug="login-fail")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect email, password, or tenant slug"


@pytest.mark.integration
async def test_login_inactive_tenant_401(uow):
    service = AuthService(uow)
    tenant = make_tenant(slug="inactive-tenant", is_active=False)
    uow.session.add(tenant)
    await uow.flush()

    user = make_user(
        tenant_id=tenant.id, email="inactive@test.com", password="correct_password"
    )
    uow.session.add(user)
    await uow.flush()

    data = LoginRequest(email="inactive@test.com", password="correct_password")
    with pytest.raises(ServiceError) as exc_info:
        await service.login(data, tenant_slug="inactive-tenant")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect email, password, or tenant slug"
