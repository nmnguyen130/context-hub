import uuid

import pytest

from app.core.context import (
    RequestContext,
    UserRole,
    bind_context,
    current_context,
    try_current_context,
)


@pytest.mark.unit
def test_bind_and_read_context():
    ctx = RequestContext(
        request_id="test-req",
        trace_id="test-trace",
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=UserRole.MEMBER,
    )
    with bind_context(ctx):
        current = current_context()
        assert current.request_id == "test-req"
        assert current.trace_id == "test-trace"
        assert current.tenant_id == ctx.tenant_id
        assert current.user_id == ctx.user_id
        assert current.role == UserRole.MEMBER

    # Outside scope should be None or raise
    assert try_current_context() is None
    with pytest.raises(RuntimeError):
        current_context()


@pytest.mark.unit
def test_context_roundtrip_dict():
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ctx = RequestContext(
        request_id="r1",
        trace_id="t1",
        tenant_id=tenant_id,
        user_id=user_id,
        role=UserRole.ADMIN,
    )
    d = ctx.to_dict()
    assert d["request_id"] == "r1"
    assert d["tenant_id"] == str(tenant_id)
    assert d["role"] == "ADMIN"

    restored = RequestContext.from_dict(d)
    assert restored.request_id == "r1"
    assert restored.tenant_id == tenant_id
    assert restored.role == UserRole.ADMIN
