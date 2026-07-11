import uuid
from contextvars import ContextVar, Token

from sqlalchemy import ForeignKey, event
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

from app.core.context import current_context_or_none


def get_current_tenant_id() -> uuid.UUID | None:
    """Gets the current tenant ID from the unified request context."""
    ctx = current_context_or_none()
    return ctx.tenant_id if ctx else None


# 2. Database manager
class Database:
    """Manages async engines and session factory lifecycles."""

    def __init__(self, url: str, pool_size: int = 10, max_overflow: int = 20, admin_url: str | None = None):
        self.engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        if not admin_url:
            if "postgres:" in url:
                admin_url = url
            elif "app_user:" in url:
                admin_url = url.replace("app_user:", "app_admin:")
            else:
                admin_url = url

        self.admin_engine = create_async_engine(
            admin_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self.admin_session_factory = async_sessionmaker(
            bind=self.admin_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    def session(self) -> AsyncSession:
        return self.session_factory()

    async def dispose(self) -> None:
        await self.engine.dispose()
        await self.admin_engine.dispose()


# Global base model
class Base(DeclarativeBase):
    pass


# Tenant-scoped base model
class TenantBaseModel(Base):
    __abstract__ = True

    # Indexed non-nullable tenant foreign key for isolation
    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            PG_UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


# Query interceptor hook for tenant isolation
@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state) -> None:
    """Intercepts ORM queries to automatically apply active tenant filtering."""
    tenant_id = get_current_tenant_id()
    if not tenant_id or execute_state.execution_options.get("skip_tenant_filter"):
        return

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantBaseModel,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
            propagate_to_loaders=True,
        )
    )


# Insert hook for implicit tenant context injection
@event.listens_for(Session, "before_flush")
def _set_tenant_id_before_flush(session, flush_context, instances) -> None:
    """Populates tenant_id on new TenantBaseModel instances before session flush."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return

    for obj in session.new:
        if isinstance(obj, TenantBaseModel) and obj.tenant_id is None:
            obj.tenant_id = tenant_id
