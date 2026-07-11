# app/modules/tenant/services/tenant_service.py
import re
from uuid import UUID
from fastapi import Depends
from app.api.deps import get_uow
from app.core.exceptions import ServiceError
from app.core.uow import UnitOfWork
from app.modules.tenant.models import Tenant
from app.modules.tenant.repository import TenantRepository
from app.modules.tenant.schemas import TenantUpdate

class TenantService:
    def __init__(self, uow: UnitOfWork = Depends(get_uow)):
        self.uow = uow

    async def get_by_id(self, tenant_id: UUID) -> Tenant:
        """Retrieves a tenant by ID."""
        tenant = await self.uow.repo(TenantRepository).get(tenant_id)
        if not tenant:
            raise ServiceError("Tenant not found", status_code=404)
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Retrieves a tenant by slug."""
        slug = slug.strip().lower()
        return await self.uow.repo(TenantRepository).get_by_slug(slug)

    async def update(self, tenant_id: UUID, data: TenantUpdate) -> Tenant:
        """Updates a tenant."""
        tenant = await self.get_by_id(tenant_id)

        updates = data.model_dump(
            exclude_none=True,
            exclude={"settings"},
        )

        for key, value in updates.items():
            setattr(tenant, key, value)

        if data.settings is not None:
            tenant.settings = {
                **(tenant.settings or {}),
                **data.settings.model_dump(mode="json", exclude_unset=True),
            }

        await self.uow.flush()
        return tenant

    async def deactivate(self, tenant_id: UUID) -> None:
        """Deactivates a tenant."""
        tenant = await self.get_by_id(tenant_id)

        if tenant.is_active:
            tenant.is_active = False
            await self.uow.flush()

    @staticmethod
    def generate_slug(name: str) -> str:
        """Generates a slug from name."""
        slug = re.sub(
            r"[\s_-]+",
            "-",
            re.sub(r"[^\w\s-]", "", name.strip().lower()),
        ).strip("-")

        return slug or "organization"
