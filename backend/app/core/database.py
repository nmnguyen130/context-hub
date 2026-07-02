import uuid
from typing import AsyncGenerator

from sqlalchemy import ForeignKey, event, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    declared_attr,
    mapped_column,
    with_loader_criteria,
)

from app.core.config import settings

# 1. Asynchronous Database Engine Config
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# 2. Asynchronous Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# 3. Base Class for all models
class Base(DeclarativeBase):
    pass


# 4. Base Class for Tenant-scoped models (Inheritors are automatically filtered)
class TenantBaseModel(Base):
    __abstract__ = True

    # tenant_id is non-nullable and indexed to secure tenant isolation in database
    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            PG_UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


# 5. Global Multi-Tenancy Query Interceptor Hook
@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    """
    SQLAlchemy Event Listener that intercepts all ORM executions.
    If tenant_id is set in tenant_id_context, it appends a global filter to
    all select, update, and delete queries for tables inheriting from TenantBaseModel.
    """
    from app.core.tenant_context import get_current_tenant_id

    tenant_id = get_current_tenant_id()
    # Check if execution requests bypassing the tenant filter (e.g. admin panels, system runs)
    skip_tenant_filter = execute_state.execution_options.get(
        "skip_tenant_filter", False
    )

    if tenant_id and not skip_tenant_filter:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                TenantBaseModel,
                lambda cls: cls.tenant_id == tenant_id,
                include_aliases=True,
                propagate_to_loaders=True,
            )
        )


# 6. Global Multi-Tenancy Insert Hook (Implicit Context Injection)
@event.listens_for(Session, "before_flush")
def _set_tenant_id_before_flush(session, flush_context, instances):
    """
    SQLAlchemy Event Listener that intercepts sessions before flush.
    If an object inherits from TenantBaseModel, and tenant_id is not set,
    it automatically populates it from the tenant_id request context.
    """
    from app.core.tenant_context import get_current_tenant_id

    tenant_id = get_current_tenant_id()
    if tenant_id:
        for obj in session.new:
            if isinstance(obj, TenantBaseModel):
                if getattr(obj, "tenant_id", None) is None:
                    obj.tenant_id = tenant_id


# 7. Dependency Provider for FastAPI Route Handlers
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a database session and closes it on request completion."""
    async with AsyncSessionLocal() as session:
        yield session
