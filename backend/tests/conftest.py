# tests/conftest.py
import uuid

import pytest
import pytest_asyncio
from app.core.enums import UserRole
from app.core.event_bus import event_bus
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.context import RequestContext, bind_context
from app.core.database import Base
from app.core.uow import UnitOfWork
from tests.models import MockScopedModel, MockTenant


@pytest_asyncio.fixture
async def test_engine():
    """Function-scoped database engine to avoid event loop conflicts."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Dynamically create test tables and configure RLS
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("GRANT ALL PRIVILEGES ON mock_tenants TO app_user, app_admin")
        )
        await conn.execute(
            text("GRANT ALL PRIVILEGES ON mock_scoped_models TO app_user, app_admin")
        )
        await conn.execute(
            text("ALTER TABLE mock_scoped_models ENABLE ROW LEVEL SECURITY")
        )
        await conn.execute(
            text("ALTER TABLE mock_scoped_models FORCE ROW LEVEL SECURITY")
        )
        await conn.execute(
            text("DROP POLICY IF EXISTS tenant_isolation ON mock_scoped_models")
        )
        await conn.execute(
            text("""
            CREATE POLICY tenant_isolation ON mock_scoped_models
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """)
        )

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Function-scoped session wrapped in a transaction that always rolls back."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        await session.begin()
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_uow(db_session):
    context = RequestContext(
        request_id="test_req",
        correlation_id="test_corr",
        tenant_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        role=UserRole.ADMIN,
        is_platform_admin=True,
    )

    class DummySessionFactory:
        def __call__(self):
            return db_session

    uow = UnitOfWork(
        session_factory=DummySessionFactory(),
        context=context,
        event_bus=event_bus,
        admin_session_factory=DummySessionFactory(),
    )
    with bind_context(context):
        yield uow
