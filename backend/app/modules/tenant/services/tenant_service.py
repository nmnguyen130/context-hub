import re
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import ServiceError
from app.modules.tenant.models import Tenant
from app.modules.tenant.schemas import TenantUpdate


class TenantService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    @staticmethod
    def _query():
        return select(Tenant).execution_options(skip_tenant_filter=True)

    async def get_by_id(self, tenant_id: UUID) -> Tenant:
        """Retrieves a tenant by ID."""
        tenant = await self.db.scalar(self._query().where(Tenant.id == tenant_id))
        if not tenant:
            raise ServiceError("Tenant not found", status_code=404)
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Retrieves a tenant by slug."""
        slug = slug.strip().lower()
        return await self.db.scalar(self._query().where(Tenant.slug == slug))

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

        await self.db.flush()
        return tenant

    async def deactivate(self, tenant_id: UUID) -> None:
        """Deactivates a tenant."""
        tenant = await self.get_by_id(tenant_id)

        if tenant.is_active:
            tenant.is_active = False
            await self.db.flush()

    @staticmethod
    def generate_slug(name: str) -> str:
        """Generates a slug from name."""
        slug = re.sub(
            r"[\s_-]+",
            "-",
            re.sub(r"[^\w\s-]", "", name.strip().lower()),
        ).strip("-")

        return slug or "organization"
