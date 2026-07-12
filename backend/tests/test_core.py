# tests/test_core.py
import uuid

import pytest
from app.core.enums import UserRole
from sqlalchemy import select, text

from app.core.context import RequestContext, bind_context
from app.core.events import DomainEvent, OutboxEvent, OutboxStatus
from tests.models import MockScopedModel, MockTenant


@pytest.mark.asyncio
async def test_rls_isolation(db_session):
    # 1. Create two test tenants (as superuser)
    t1_id = uuid.uuid4()
    t2_id = uuid.uuid4()

    tenant1 = MockTenant(id=t1_id, name="Tenant 1")
    tenant2 = MockTenant(id=t2_id, name="Tenant 2")
    db_session.add_all([tenant1, tenant2])
    await db_session.flush()

    # 2. Add scoped record for Tenant 1 and Tenant 2
    rec1 = MockScopedModel(id=uuid.uuid4(), tenant_id=t1_id, name="Record Tenant 1")
    rec2 = MockScopedModel(id=uuid.uuid4(), tenant_id=t2_id, name="Record Tenant 2")
    db_session.add_all([rec1, rec2])
    await db_session.flush()

    # 3. Query under Tenant 1 context (switching role to app_user to activate RLS)
    ctx1 = RequestContext(
        request_id="req1",
        correlation_id="corr1",
        tenant_id=t1_id,
        actor_id=uuid.uuid4(),
        role=UserRole.MEMBER,
    )
    with bind_context(ctx1):
        await db_session.execute(text("SET ROLE app_user"))
        await db_session.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(t1_id)}
        )

        stmt = select(MockScopedModel)
        res = await db_session.execute(stmt)
        records = res.scalars().all()

        assert len(records) == 1
        assert records[0].id == rec1.id
        assert records[0].name == "Record Tenant 1"

        await db_session.execute(text("RESET ROLE"))

    # 4. Query under Tenant 2 context (switching role to app_user to activate RLS)
    ctx2 = RequestContext(
        request_id="req2",
        correlation_id="corr2",
        tenant_id=t2_id,
        actor_id=uuid.uuid4(),
        role=UserRole.MEMBER,
    )
    with bind_context(ctx2):
        await db_session.execute(text("SET ROLE app_user"))
        await db_session.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(t2_id)}
        )

        stmt = select(MockScopedModel)
        res = await db_session.execute(stmt)
        records = res.scalars().all()

        assert len(records) == 1
        assert records[0].id == rec2.id
        assert records[0].name == "Record Tenant 2"

        await db_session.execute(text("RESET ROLE"))


@pytest.mark.asyncio
async def test_domain_event_autocapture(test_uow):
    async with test_uow as uow:
        # Create and flush the test tenant
        tenant_id = uow._context.tenant_id
        tenant = MockTenant(id=tenant_id, name="Auto Tenant")
        uow.session.add(tenant)
        await uow.flush()

        # Create record and record a domain event directly on the entity
        record = MockScopedModel(
            id=uuid.uuid4(), tenant_id=tenant_id, name="Scoped Record"
        )
        record.record_event(
            DomainEvent(
                event_type="record.created",
                payload={"name": "Scoped Record", "action": "test"},
            )
        )

        uow.session.add(record)

        # Commit the transaction (this triggers before_flush event listener)
        await uow.commit()

        # Query the outbox table to check if event was auto-captured
        stmt = select(OutboxEvent).where(OutboxEvent.tenant_id == tenant_id)
        res = await uow.session.execute(stmt)
        outbox_events = res.scalars().all()

        assert len(outbox_events) == 1
        assert outbox_events[0].event_type == "record.created"
        assert outbox_events[0].payload == {"name": "Scoped Record", "action": "test"}
        assert outbox_events[0].status == OutboxStatus.PENDING
