import uuid

import pytest
from sqlalchemy import select, text

from app.core.context import RequestContext, UserRole
from app.core.events import OutboxEvent, OutboxStatus
from app.core.uow import UnitOfWork
from app.modules.tenant.models import Tenant
from tests.factories import make_tenant


@pytest.mark.integration
async def test_commit_persists(test_engine):
    ctx = RequestContext(
        request_id="test", trace_id="test", tenant_id=uuid.uuid4(), role=UserRole.ADMIN
    )
    async_session = (
        UnitOfWork.__init__.__defaults__ or None
    )  # we will use test_engine session factory
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async with UnitOfWork(
        session_factory=session_factory, context=ctx, is_admin=True
    ) as uow:
        tenant = make_tenant(name="Persist Corp")
        uow.session.add(tenant)
        await uow.commit()
        tenant_id = tenant.id

    # Verify in a clean session
    async with session_factory() as session:
        retrieved = await session.get(Tenant, tenant_id)
        assert retrieved is not None
        assert retrieved.name == "Persist Corp"

        # Cleanup
        await session.delete(retrieved)
        await session.commit()


@pytest.mark.integration
async def test_rollback_discards(test_engine):
    ctx = RequestContext(
        request_id="test", trace_id="test", tenant_id=uuid.uuid4(), role=UserRole.ADMIN
    )
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async with UnitOfWork(
        session_factory=session_factory, context=ctx, is_admin=True
    ) as uow:
        tenant = make_tenant(name="Discard Corp")
        uow.session.add(tenant)
        # Rollback happens on exit if no commit is called

    async with session_factory() as session:
        stmt = select(Tenant).where(Tenant.name == "Discard Corp")
        retrieved = await session.scalar(stmt)
        assert retrieved is None
