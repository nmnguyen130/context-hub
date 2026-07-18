import uuid

import jwt
import pytest

from app.core.context import UserRole
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


@pytest.mark.unit
def test_hash_verify_password():
    pwd = "MySecretPassword123!"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(pwd, h) is True
    assert verify_password("wrong", h) is False
    assert verify_password(pwd, None) is False


@pytest.mark.unit
def test_72_byte_truncation():
    # Bcrypt truncates at 72 bytes. Verify we handle this cleanly.
    long_pwd_1 = "a" * 72
    long_pwd_2 = "a" * 100
    h1 = hash_password(long_pwd_1)
    # The first 72 bytes are the same, so checkpw should evaluate them as equal
    assert verify_password(long_pwd_2, h1) is True


@pytest.mark.unit
def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(user_id, tenant_id, UserRole.MEMBER, plan="pro")

    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == UserRole.MEMBER.value
    assert payload["plan"] == "pro"
    assert payload["type"] == "access"


@pytest.mark.unit
def test_refresh_token_roundtrip():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token, jti, expires = create_refresh_token(user_id, tenant_id)

    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


@pytest.mark.unit
def test_decode_wrong_type_raises():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(user_id, tenant_id, UserRole.MEMBER)

    with pytest.raises(ValueError):
        decode_token(token, expected_type="refresh")


@pytest.mark.unit
def test_hash_token_deterministic():
    tok = "my-jwt-token-string"
    h1 = hash_token(tok)
    h2 = hash_token(tok)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex string
