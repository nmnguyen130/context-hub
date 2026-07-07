from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
from app.core.config import settings
from app.main import app

# Create a test-specific engine using NullPool to prevent connection caching
# across different asyncio event loops during test execution.
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> None:
    """Automatically truncates all tables before each test to guarantee database freshness."""
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE document_chunks, documents, audit_logs, workspaces, users, tenants, refresh_tokens, invitations CASCADE;"
            )
        )


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session and rolls back transactions after each test."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yields an HTTPX AsyncClient with overridden db session dependency."""

    async def override_get_db():
        yield db

    if not hasattr(app.state, "db"):
        from app.core.database import Database

        app.state.db = Database(settings.DATABASE_URL)
    if not hasattr(app.state, "redis"):
        import redis.asyncio as aioredis

        app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    if not hasattr(app.state, "storage"):
        from app.core.storage import S3StorageProvider

        app.state.storage = S3StorageProvider()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
