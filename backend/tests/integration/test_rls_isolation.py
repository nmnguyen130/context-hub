import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.context import RequestContext, UserRole
from app.core.uow import UnitOfWork
from app.modules.auth.models import User, Invitation
from tests.factories import make_tenant, make_user, make_invitation


@pytest.mark.integration
async def test_rls_select_isolation(test_engines):
    """Verify that a tenant-scoped session cannot select rows belonging to other tenants."""
    app_engine, owner_engine = test_engines
    tenant_a = make_tenant(slug="tenant-a")
    tenant_b = make_tenant(slug="tenant-b")
    
    app_session_factory = async_sessionmaker(bind=app_engine, expire_on_commit=False)
    owner_session_factory = async_sessionmaker(bind=owner_engine, expire_on_commit=False)
    
    # 1. Create resources under Tenant A and Tenant B using an admin/bypass UoW (owner_engine)
    admin_ctx = RequestContext(request_id="test", trace_id="test", tenant_id=None, user_id=None, role=UserRole.SUPER_ADMIN)
    async with UnitOfWork(session_factory=owner_session_factory, context=admin_ctx, is_admin=True) as uow:
        uow.session.add(tenant_a)
        uow.session.add(tenant_b)
        await uow.flush()
        
        user_a = make_user(tenant_id=tenant_a.id, email="usera@tenant-a.com")
        user_b = make_user(tenant_id=tenant_b.id, email="userb@tenant-b.com")
        uow.session.add(user_a)
        uow.session.add(user_b)
        await uow.commit()
        user_a_id = user_a.id
        user_b_id = user_b.id

    # 2. Query within a Tenant A scoped session — should not see Tenant B rows (app_engine)
    ctx_a = RequestContext(
        request_id="test",
        trace_id="test",
        tenant_id=tenant_a.id,
        user_id=user_a_id,
        role=UserRole.MEMBER
    )
    async with UnitOfWork(session_factory=app_session_factory, context=ctx_a, is_admin=False) as uow:
        # Verify broad select only returns user A
        stmt = select(User)
        users = (await uow.session.scalars(stmt)).all()
        assert len(users) == 1
        assert users[0].id == user_a_id
        
        # Verify that querying directly by user B ID returns None (RLS blocks/hides it)
        user_b_retrieved = await uow.session.get(User, user_b_id)
        assert user_b_retrieved is None


@pytest.mark.integration
async def test_rls_insert_violation(test_engines):
    """Verify that a tenant-scoped session raises a CheckViolation if trying to write another tenant's data."""
    app_engine, owner_engine = test_engines
    tenant_a = make_tenant(slug="tenant-a")
    tenant_b = make_tenant(slug="tenant-b")
    
    app_session_factory = async_sessionmaker(bind=app_engine, expire_on_commit=False)
    owner_session_factory = async_sessionmaker(bind=owner_engine, expire_on_commit=False)
    
    admin_ctx = RequestContext(request_id="test", trace_id="test", tenant_id=None, user_id=None, role=UserRole.SUPER_ADMIN)
    async with UnitOfWork(session_factory=owner_session_factory, context=admin_ctx, is_admin=True) as uow:
        uow.session.add(tenant_a)
        uow.session.add(tenant_b)
        await uow.commit()

    ctx_a = RequestContext(
        request_id="test",
        trace_id="test",
        tenant_id=tenant_a.id,
        user_id=uuid.uuid4(),
        role=UserRole.MEMBER
    )
    
    # Try inserting a User for Tenant B inside Tenant A's UoW transaction (app_engine)
    async with UnitOfWork(session_factory=app_session_factory, context=ctx_a, is_admin=False) as uow:
        bad_user = make_user(tenant_id=tenant_b.id, email="bad@test.com")
        uow.session.add(bad_user)
        
        with pytest.raises(DBAPIError) as exc_info:
            await uow.commit()
            
        # Verify database check policy blocks write
        assert "violates row-level security policy" in str(exc_info.value)
