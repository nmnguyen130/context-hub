# app/modules/tenant/repository.py
from app.core.repository import Repository
from app.modules.tenant.models import Tenant

class TenantRepository(Repository[Tenant]):
    model = Tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        return await self.session.scalar(self.query().where(Tenant.slug == slug))
