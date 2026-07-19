import uuid

import jwt
import pytest

from app.core.context import (
    RequestContext,
    UserRole,
    bind_context,
    current_context,
    try_current_context,
)
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


@pytest.mark.unit
def test_bcrypt_password_hashing():
    pwd = "EnterprisePassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password(pwd, None) is False


@pytest.mark.unit
def test_jwt_access_and_refresh_tokens():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    # Test Access Token
    access_tok = create_access_token(user_id, tenant_id, UserRole.ADMIN, plan="pro")
    payload = decode_token(access_tok, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == UserRole.ADMIN.value
    assert payload["plan"] == "pro"

    # Test Refresh Token
    refresh_tok, jti, expires = create_refresh_token(user_id, tenant_id)
    payload_refresh = decode_token(refresh_tok, expected_type="refresh")
    assert payload_refresh["sub"] == str(user_id)
    assert payload_refresh["tenant_id"] == str(tenant_id)
    assert payload_refresh["jti"] == jti


@pytest.mark.unit
def test_jwt_decode_type_validation():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    access_tok = create_access_token(user_id, tenant_id, UserRole.MEMBER)

    with pytest.raises(ValueError, match="Expected token type"):
        decode_token(access_tok, expected_type="refresh")


@pytest.mark.unit
def test_request_context_propagation():
    ctx = RequestContext(
        request_id="req-123",
        trace_id="trace-123",
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=UserRole.MEMBER,
    )

    # Before binding
    assert try_current_context() is None
    with pytest.raises(RuntimeError):
        current_context()

    # With binding
    with bind_context(ctx):
        current = current_context()
        assert current.request_id == "req-123"
        assert current.trace_id == "trace-123"
        assert current.tenant_id == ctx.tenant_id
        assert current.user_id == ctx.user_id
        assert current.role == UserRole.MEMBER

    # After binding exits
    assert try_current_context() is None
