# tests/test_rls_isolation.py
import pytest
import uuid
from sqlalchemy import text, select
from app.core.context import RequestContext, bind_context
from app.core.enums import PlanTier, UserRole
from app.modules.tenant.models import Tenant
from app.modules.documents.models import Document

@pytest.mark.asyncio
async def test_rls_enforcement(db_session):
    # 1. Create two tenants
    t1_id = uuid.uuid4()
    t2_id = uuid.uuid4()

    tenant1 = Tenant(id=t1_id, name="Tenant 1", slug="tenant1", plan_tier=PlanTier.STARTER, settings={})
    tenant2 = Tenant(id=t2_id, name="Tenant 2", slug="tenant2", plan_tier=PlanTier.STARTER, settings={})
    db_session.add_all([tenant1, tenant2])
    await db_session.flush()

    # 2. Add document for Tenant 1
    doc1 = Document(
        id=uuid.uuid4(),
        tenant_id=t1_id,
        name="Doc Tenant 1",
        file_type="txt",
        object_store_key="key1",
        status="ACTIVE",
        file_size=100
    )
    # Add document for Tenant 2
    doc2 = Document(
        id=uuid.uuid4(),
        tenant_id=t2_id,
        name="Doc Tenant 2",
        file_type="txt",
        object_store_key="key2",
        status="ACTIVE",
        file_size=200
    )
    db_session.add_all([doc1, doc2])
    await db_session.flush()

    # 3. Query under Tenant 1 context
    ctx1 = RequestContext(
        request_id="req1",
        correlation_id="corr1",
        tenant_id=t1_id,
        actor_id=uuid.uuid4(),
        role=UserRole.MEMBER
    )
    with bind_context(ctx1):
        # Set GUC
        await db_session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(t1_id)})
        
        # Query documents (broad select without manual filter!)
        stmt = select(Document)
        res = await db_session.execute(stmt)
        docs = res.scalars().all()
        
        assert len(docs) == 1
        assert docs[0].id == doc1.id
        assert docs[0].name == "Doc Tenant 1"

    # 4. Query under Tenant 2 context
    ctx2 = RequestContext(
        request_id="req2",
        correlation_id="corr2",
        tenant_id=t2_id,
        actor_id=uuid.uuid4(),
        role=UserRole.MEMBER
    )
    with bind_context(ctx2):
        # Set GUC
        await db_session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(t2_id)})
        
        # Query documents
        stmt = select(Document)
        res = await db_session.execute(stmt)
        docs = res.scalars().all()
        
        assert len(docs) == 1
        assert docs[0].id == doc2.id
        assert docs[0].name == "Doc Tenant 2"
