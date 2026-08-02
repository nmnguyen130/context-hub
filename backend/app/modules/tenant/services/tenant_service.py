import re
import uuid

from sqlalchemy import select

from app.core.exceptions import ServiceError
from app.core.pagination import CursorParams, paginate_cursor
from app.core.uow import UnitOfWork
from app.modules.tenant.models import Tenant
from app.modules.tenant.schemas import TenantCreate, TenantUpdate


def generate_slug(name: str, fallback: str = "organization") -> str:
    """Generate a URL-safe lowercase slug from a name."""
    slug = re.sub(
        r"[\s_-]+",
        "-",
        re.sub(r"[^\w\s-]", "", name.strip().lower()),
    ).strip("-")
    return slug or fallback


class TenantService:
    """Application service for tenant management."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_by_id(
        self, tenant_id: uuid.UUID, include_inactive: bool = False
    ) -> Tenant:
        """Retrieve a tenant by ID, raising 404 if not found or inactive."""
        tenant = await self.uow.session.get(Tenant, tenant_id)
        if tenant is None or (not include_inactive and not tenant.is_active):
            raise ServiceError.not_found("Tenant")
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """Retrieve an active tenant by slug, returning None if not found or inactive."""
        return await self.uow.session.scalar(
            select(Tenant).where(
                Tenant.slug == slug.strip().lower(),
                Tenant.is_active.is_(True),
            )
        )

    async def list(
        self,
        params: CursorParams | None = None,
        search: str | None = None,
        order_by: str = "created_at",
    ) -> tuple[list[Tenant], str | None, bool]:
        """List active tenants with pagination and optional search filter."""
        params = params or CursorParams()
        stmt = select(Tenant).where(Tenant.is_active.is_(True))

        if search:
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(Tenant.name.ilike(term) | Tenant.slug.ilike(term))

        order_columns = {
            "name": Tenant.name,
            "slug": Tenant.slug,
            "created_at": Tenant.created_at,
            "plan_tier": Tenant.plan_tier,
        }

        sort_col = order_columns.get(order_by.lower().strip())
        if sort_col is None:
            raise ServiceError.unprocessable(f"Invalid sort column: {order_by}")

        return await paginate_cursor(
            self.uow.session,
            stmt,
            params,
            sort_column=sort_col,
            id_column=Tenant.id,
        )

    async def create(self, data: TenantCreate) -> Tenant:
        """Prepare and persist a new Tenant."""
        slug = generate_slug(data.slug if data.slug else data.name)

        existing = await self.uow.session.scalar(
            select(Tenant).where(Tenant.slug == slug)
        )
        if existing:
            raise ServiceError.conflict("Tenant slug already exists.")

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
