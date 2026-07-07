from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_admin_user,
    get_current_user,
    get_db,
)
from app.modules.auth.models import User
from app.modules.tenant.schemas import (
    TenantResolveResponse,
    TenantResponse,
    TenantStatsResponse,
    TenantUpdate,
)
from app.modules.tenant.services.tenant_service import TenantService
from app.modules.tenant.services.tenant_stats_service import TenantStatsService

tenant_router = APIRouter(prefix="/tenant", tags=["Tenant"])
tenants_router = APIRouter(prefix="/tenants", tags=["Tenants"])


@tenant_router.get("", response_model=TenantResponse)
async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(),
):
    """Gets active tenant details."""
    return await tenant_service.get_by_id(current_user.tenant_id)


@tenant_router.patch("", response_model=TenantResponse, status_code=status.HTTP_200_OK)
async def update_current_tenant(
    data: TenantUpdate,
    current_user: User = Depends(get_current_admin_user),
    tenant_service: TenantService = Depends(),
):
    """Updates tenant. Admin only."""
    return await tenant_service.update(current_user.tenant_id, data)


@tenant_router.get("/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(
    current_user: User = Depends(get_current_admin_user),
    stats_service: TenantStatsService = Depends(),
):
    """Gets tenant statistics. Admin only."""
    return await stats_service.get_stats(current_user.tenant_id)


@tenants_router.get("/lookup/{slug}", response_model=TenantResolveResponse)
async def resolve_tenant_slug(
    slug: str,
    tenant_service: TenantService = Depends(),
):
    """Resolves a tenant slug."""
    tenant = await tenant_service.get_by_slug(slug)
    return TenantResolveResponse(
        exists=tenant is not None,
        name=tenant.name if tenant else None,
    )
