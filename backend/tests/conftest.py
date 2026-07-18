import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_authenticated_context, get_public_uow, get_uow
from app.core.config import settings
from app.core.context import RequestContext, UserRole, bind_context, current_context
from app.core.database import Base
from app.core.uow import UnitOfWork
from app.main import app

TEST_DATABASE_URL = settings.DATABASE_URL.replace(f"/{settings.POSTGRES_DB}", f"/{settings.POSTGRES_DB}_test")


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(test_engine):
    """Automatically cleans all database tables before each test to ensure isolation."""
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provides a database session for test setup."""
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def uow(test_engine) -> AsyncGenerator[UnitOfWork, None]:
    """Provides an admin-bypassed Unit of Work targeting the test database."""
    ctx = RequestContext(
        request_id="test-req",
        trace_id="test-trace",
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=UserRole.ADMIN,
    )
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with UnitOfWork(
        session_factory=session_factory, context=ctx, is_admin=True
    ) as unit:
        yield unit


@pytest_asyncio.fixture
async def async_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient with database dependencies overridden to target the test database."""
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_uow(
        context: RequestContext = Depends(get_authenticated_context),
    ):
        async with UnitOfWork(
            session_factory=session_factory,
            context=context,
            is_admin=False,
        ) as unit:
            yield unit

    async def override_get_public_uow():
        async with UnitOfWork(
            session_factory=session_factory,
            context=current_context(),
            is_admin=True,
        ) as unit:
            yield unit

    app.dependency_overrides[get_uow] = override_get_uow
    app.dependency_overrides[get_public_uow] = override_get_public_uow

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
