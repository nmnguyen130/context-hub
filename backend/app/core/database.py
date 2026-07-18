import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


def create_engine_from_settings(url: str | None = None):
    return create_async_engine(
        url or settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


engine = create_engine_from_settings()

async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
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
    async with async_session() as session:
        yield session
