import os
import subprocess
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_authenticated_context, get_public_uow, get_uow
from app.core.config import settings
from app.core.context import RequestContext, UserRole, current_context
from app.core.database import Base
from app.core.uow import UnitOfWork
from app.main import app

TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    f"/{settings.POSTGRES_DB}", f"/{settings.POSTGRES_DB}_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engines():
    # 1. Build test DB connection strings using configuration variables
    test_owner_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_OWNER_USER}:{settings.POSTGRES_OWNER_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}_test"
    )
    test_app_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_APP_USER}:{settings.POSTGRES_APP_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}_test"
    )

    # 3. Create the test engines
    app_engine = create_async_engine(test_app_url)
    owner_engine = create_async_engine(test_owner_url)

    # 4. Clean up test database (recreate public schema) to eliminate existing tables/types
    async with owner_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        # Re-apply the default privileges inside the newly created schema
        await conn.execute(text(f"ALTER DEFAULT PRIVILEGES FOR ROLE {settings.POSTGRES_OWNER_USER} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {settings.POSTGRES_APP_USER};"))
        await conn.execute(text(f"ALTER DEFAULT PRIVILEGES FOR ROLE {settings.POSTGRES_OWNER_USER} IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {settings.POSTGRES_APP_USER};"))

    # 5. Run migrations on the test database using the admin/owner role
    env = {**os.environ, "DATABASE_OWNER_URL": test_owner_url}
    subprocess.run(["alembic", "upgrade", "head"], env=env, check=True)
    
    yield app_engine, owner_engine
    
    await app_engine.dispose()
    await owner_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(test_engines):
    """Clean all tables before each test using the owner engine (bypasses RLS naturally)."""
    app_engine, owner_engine = test_engines
    async with owner_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


from sqlalchemy import event

@pytest_asyncio.fixture
async def db_session(test_engines) -> AsyncGenerator[AsyncSession, None]:
    """Database session for test setup (uses owner engine to naturally bypass RLS)."""
    app_engine, owner_engine = test_engines
    session_factory = async_sessionmaker(bind=owner_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def uow(test_engines) -> AsyncGenerator[UnitOfWork, None]:
    """Admin-mode Unit of Work using the owner session factory (bypasses RLS naturally)."""
    app_engine, owner_engine = test_engines
    ctx = RequestContext(
        request_id="test-req",
        trace_id="test-trace",
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=UserRole.ADMIN,
    )
    session_factory = async_sessionmaker(bind=owner_engine, expire_on_commit=False)
    async with UnitOfWork(
        session_factory=session_factory, context=ctx, is_admin=True
    ) as unit:
        yield unit


@pytest_asyncio.fixture
def make_tenant_uow(test_engines):
    """Factory to create a tenant-scoped Unit of Work with RLS active (uses app engine)."""
    app_engine, owner_engine = test_engines
    session_factory = async_sessionmaker(bind=app_engine, expire_on_commit=False)

    def _make(tenant_id: uuid.UUID, user_id: uuid.UUID | None = None, role: UserRole = UserRole.MEMBER):
        ctx = RequestContext(
            request_id="test-req",
            trace_id="test-trace",
            tenant_id=tenant_id,
            user_id=user_id or uuid.uuid4(),
            role=role,
        )
        return UnitOfWork(session_factory=session_factory, context=ctx, is_admin=False)

    return _make


@pytest_asyncio.fixture
async def async_client(test_engines) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient with overridden dependencies for DB access."""
    app_engine, owner_engine = test_engines
    app_session_factory = async_sessionmaker(bind=app_engine, expire_on_commit=False)
    owner_session_factory = async_sessionmaker(bind=owner_engine, expire_on_commit=False)

    async def override_get_uow(
        context: RequestContext = Depends(get_authenticated_context),
    ):
        async with UnitOfWork(
            session_factory=app_session_factory,
            context=context,
            is_admin=False,
        ) as unit:
            yield unit

    async def override_get_public_uow():
        async with UnitOfWork(
            session_factory=owner_session_factory,
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
