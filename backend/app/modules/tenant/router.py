from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    get_authenticated_context,
    get_service,
    require_roles,
)
from app.core.context import RequestContext, UserRole
from app.modules.tenant.schemas import (
    TenantListResponse,
    TenantResponse,
    TenantStatsResponse,
    TenantUpdate,
)
from app.modules.tenant.services import TenantService, TenantStatsService

tenant_router = APIRouter(prefix="/tenant", tags=["Tenant"])
tenants_router = APIRouter(prefix="/tenants", tags=["Tenants"])


@tenant_router.get("", response_model=TenantResponse)
async def get_current_tenant(
    context: RequestContext = Depends(get_authenticated_context),
    tenant_service: TenantService = Depends(get_service(TenantService)),
):
    """Gets active tenant details."""
    return await tenant_service.get_by_id(context.tenant_id)


@tenant_router.patch("", response_model=TenantResponse, status_code=status.HTTP_200_OK)
async def update_current_tenant(
    data: TenantUpdate,
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    tenant_service: TenantService = Depends(get_service(TenantService)),
):
    """Updates tenant details."""
    tenant = await tenant_service.update(context.tenant_id, data)
    await tenant_service.uow.commit()
    await tenant_service.uow.session.refresh(tenant)
    return tenant


@tenant_router.get("/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(
    context: RequestContext = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
    stats_service: TenantStatsService = Depends(get_service(TenantStatsService)),
):
    """Gets tenant resources usage statistics."""
    return await stats_service.get_stats(context.tenant_id)


@tenants_router.get(
    "",
    response_model=TenantListResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def list_tenants(
    limit: int = 10,
    offset: int = 0,
    search: str | None = None,
    order_by: str = "created_at",
    tenant_service: TenantService = Depends(get_service(TenantService, public=True)),
):
    """Lists all system tenants."""
    items, total = await tenant_service.list(
        limit=limit, offset=offset, search=search, order_by=order_by
    )
    return TenantListResponse(items=items, total=total)


@tenants_router.get("/lookup/{slug}")
async def resolve_tenant_slug(
    slug: str,
    tenant_service: TenantService = Depends(get_service(TenantService, public=True)),
):
    """Resolves organization existence by slug."""
    tenant = await tenant_service.get_by_slug(slug)
    return {
        "exists": tenant is not None,
        "name": tenant.name if tenant else None,
    }


@tenants_router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def delete_tenant(
    tenant_id: UUID,
    tenant_service: TenantService = Depends(get_service(TenantService, public=True)),
):
    """Soft-deletes a tenant account."""
    await tenant_service.delete(tenant_id)
    await tenant_service.uow.commit()
