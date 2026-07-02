import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Create a test-specific engine using NullPool to prevent connection caching
# across different asyncio event loops during test execution.
test_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool
)

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session and rolls back transactions after each test."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()
