# tests/test_uow_commit.py
import pytest
import uuid
from sqlalchemy import select
from app.core.events import DomainEvent, OutboxEvent, OutboxStatus
from app.core.uow import UnitOfWork
from app.modules.tenant.models import Tenant
from app.modules.tenant.repository import TenantRepository
from app.core.enums import PlanTier

@pytest.mark.asyncio
async def test_uow_commit_persists_outbox_events(test_uow):
    event = DomainEvent(
        event_type="test.event",
        payload={"message": "hello world"}
    )

    async with test_uow as uow:
        # Create and flush the test tenant first to avoid ForeignKeyViolation on audit_logs
        tenant_id = uow._context.tenant_id
        tenant = Tenant(
            id=tenant_id,
            name="Test UoW Tenant",
            slug="testuowtenant",
            plan_tier=PlanTier.STARTER,
            settings={}
        )
        await uow.repo(TenantRepository).add(tenant)
        await uow.flush()  # Ensures the tenant row exists before any events trigger audit logging

        uow.record_event(event)

        # Commit UoW
        await uow.commit()

        # Query outbox events
        stmt = select(OutboxEvent).where(OutboxEvent.tenant_id == tenant_id)
        res = await uow.session.execute(stmt)
        outbox_events = res.scalars().all()

        assert len(outbox_events) == 1
        assert outbox_events[0].event_type == "test.event"
        assert outbox_events[0].payload == {"message": "hello world"}
        assert outbox_events[0].status == OutboxStatus.PENDING.value
