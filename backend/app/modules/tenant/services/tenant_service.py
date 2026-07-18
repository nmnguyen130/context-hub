import re
import uuid

from sqlalchemy import func, select

from app.core.exceptions import ServiceError
from app.core.pagination import PaginationParams
from app.core.uow import UnitOfWork
from app.modules.tenant.models import Tenant
from app.modules.tenant.schemas import TenantCreate, TenantUpdate


class TenantService:
    """Application service for tenant management."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant:
        """Retrieve a tenant by ID, raising 404 if not found."""
        tenant = await self.uow.session.get(Tenant, tenant_id)
        if tenant is None:
            raise ServiceError("Tenant not found.", status_code=404)
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Retrieve a tenant by slug, returning None if not found."""
        return await self.uow.session.scalar(
            select(Tenant).where(Tenant.slug == slug.strip().lower())
        )

    async def list(
        self,
        pagination: PaginationParams = PaginationParams(),
        search: str | None = None,
        order_by: str = "created_at",
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination, search, and ordering constraints."""
        stmt = select(Tenant)

        if search:
            search_query = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                Tenant.name.ilike(search_query) | Tenant.slug.ilike(search_query)
            )

        order_columns = {
            "name": Tenant.name,
            "slug": Tenant.slug,
            "created_at": Tenant.created_at,
            "plan_tier": Tenant.plan_tier,
        }
        
        normalized_order = order_by.lower().strip()
        if normalized_order not in order_columns:
            raise ServiceError(f"Invalid sort column: {order_by}", status_code=422)
            
        sort_col = order_columns[normalized_order]
        stmt = stmt.order_by(sort_col)

        # Count total matching records before applying pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.uow.session.scalar(count_stmt) or 0

        # Retrieve the paginated items
        paginated_stmt = stmt.offset(pagination.offset).limit(pagination.limit)
        items = (await self.uow.session.scalars(paginated_stmt)).all()

        return list(items), total

    async def create(self, data: TenantCreate) -> Tenant:
        """Prepare and persist a new Tenant."""
        slug = (
            self.generate_slug(data.slug)
            if data.slug
            else self.generate_slug(data.name)
        )

        if await self.get_by_slug(slug):
            raise ServiceError("Tenant slug already exists.", status_code=409)

        tenant = Tenant(name=data.name.strip(), slug=slug)
        self.uow.session.add(tenant)
        await self.uow.flush()
        return tenant

    async def update(self, tenant_id: uuid.UUID, data: TenantUpdate) -> Tenant:
        """Update Tenant details."""
        tenant = await self.get_by_id(tenant_id)

        values = data.model_dump(exclude_unset=True)
        values.pop("slug", None)

        for key, value in values.items():
            setattr(tenant, key, value)

        await self.uow.flush()
        return tenant

    async def delete(self, tenant_id: uuid.UUID) -> None:
        """Soft-delete a tenant by setting is_active to False."""
        tenant = await self.get_by_id(tenant_id)
        tenant.is_active = False
        await self.uow.flush()

    @staticmethod
    def generate_slug(name: str) -> str:
        """Generate a URL-safe lowercase slug from a name."""
        slug = re.sub(
            r"[\s_-]+",
            "-",
            re.sub(r"[^\w\s-]", "", name.strip().lower()),
        ).strip("-")
        return slug or "organization"
