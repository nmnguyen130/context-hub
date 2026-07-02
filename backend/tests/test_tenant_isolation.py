import uuid
import pytest
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_current_tenant_id, reset_current_tenant_id
from app.modules.tenant.models import Tenant
from app.modules.documents.models import Workspace

@pytest.mark.asyncio
async def test_tenant_query_isolation(db: AsyncSession):
    # 1. Create two tenants
    tenant_a = Tenant(name="Tenant A", plan_tier="Enterprise")
    tenant_b = Tenant(name="Tenant B", plan_tier="Starter")
    db.add_all([tenant_a, tenant_b])
    await db.commit()

    # 2. Add workspaces for both tenants under their respective contexts
    token_a = set_current_tenant_id(tenant_a.id)
    workspace_a = Workspace(name="Workspace A")
    db.add(workspace_a)
    await db.commit()
    reset_current_tenant_id(token_a)

    token_b = set_current_tenant_id(tenant_b.id)
    workspace_b = Workspace(name="Workspace B")
    db.add(workspace_b)
    await db.commit()
    reset_current_tenant_id(token_b)

    # 3. Test SELECT isolation under Tenant A context
    token = set_current_tenant_id(tenant_a.id)
    try:
        stmt = select(Workspace)
        result = await db.execute(stmt)
        workspaces = result.scalars().all()
        
        # Should ONLY return Workspace A
        assert len(workspaces) == 1
        assert workspaces[0].name == "Workspace A"
        assert workspaces[0].tenant_id == tenant_a.id
    finally:
        reset_current_tenant_id(token)

    # 4. Test SELECT isolation under Tenant B context
    token = set_current_tenant_id(tenant_b.id)
    try:
        stmt = select(Workspace)
        result = await db.execute(stmt)
        workspaces = result.scalars().all()
        
        # Should ONLY return Workspace B
        assert len(workspaces) == 1
        assert workspaces[0].name == "Workspace B"
        assert workspaces[0].tenant_id == tenant_b.id
    finally:
        reset_current_tenant_id(token)

    # 5. Test bypass filter using skip_tenant_filter execution option
    token = set_current_tenant_id(tenant_a.id)
    try:
        stmt = select(Workspace).execution_options(skip_tenant_filter=True)
        result = await db.execute(stmt)
        workspaces = result.scalars().all()
        
        # Should return both workspaces
        names = [w.name for w in workspaces]
        assert "Workspace A" in names
        assert "Workspace B" in names
    finally:
        reset_current_tenant_id(token)

@pytest.mark.asyncio
async def test_tenant_update_delete_isolation(db: AsyncSession):
    tenant_a = Tenant(name="Tenant A")
    tenant_b = Tenant(name="Tenant B")
    db.add_all([tenant_a, tenant_b])
    await db.commit()

    # Create workspace in Tenant A
    token_a = set_current_tenant_id(tenant_a.id)
    workspace_a = Workspace(name="Original A")
    db.add(workspace_a)
    await db.commit()
    reset_current_tenant_id(token_a)

    # Attempt to update Workspace A under Tenant B context
    token_b = set_current_tenant_id(tenant_b.id)
    try:
        stmt = update(Workspace).where(Workspace.id == workspace_a.id).values(name="Hacked")
        result = await db.execute(stmt)
        await db.commit()
        # Since the filter is appended (tenant_id == tenant_b.id), no rows should be updated!
        assert result.rowcount == 0
    finally:
        reset_current_tenant_id(token_b)

    # Verify Workspace A remains unchanged
    token_a = set_current_tenant_id(tenant_a.id)
    try:
        stmt = select(Workspace).where(Workspace.id == workspace_a.id)
        res = await db.execute(stmt)
        w = res.scalar_one()
        assert w.name == "Original A"
    finally:
        reset_current_tenant_id(token_a)

    # Attempt to delete Workspace A under Tenant B context
    token_b = set_current_tenant_id(tenant_b.id)
    try:
        stmt = delete(Workspace).where(Workspace.id == workspace_a.id)
        result = await db.execute(stmt)
        await db.commit()
        # No rows should be deleted
        assert result.rowcount == 0
    finally:
        reset_current_tenant_id(token_b)

    # Verify Workspace A still exists
    token_a = set_current_tenant_id(tenant_a.id)
    try:
        stmt = select(Workspace).where(Workspace.id == workspace_a.id)
        res = await db.execute(stmt)
        assert res.scalar_one_or_none() is not None
    finally:
        reset_current_tenant_id(token_a)
