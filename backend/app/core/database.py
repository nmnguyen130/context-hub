import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


# App Engine — contexthub_app role, RLS enforced
app_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

app_session = async_sessionmaker(
    bind=app_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Owner Engine — postgres role, DDL and migrations (bypasses RLS naturally)
owner_engine = create_async_engine(
    settings.DATABASE_OWNER_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_OWNER_POOL_SIZE,
    max_overflow=0,
)

owner_session = async_sessionmaker(
    bind=owner_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models."""

    pass


class TenantBaseModel(Base):
    """Abstract base class for all tenant-scoped database models."""

    __abstract__ = True

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )


async def get_session():
    """FastAPI dependency yielding a raw database session lifecycle."""
    async with app_session() as session:
        yield session
