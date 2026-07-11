# tests/conftest.py
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.api.deps import get_db, get_uow
from app.core.config import settings
from app.core.context import RequestContext, bind_context
from app.core.enums import UserRole
from app.core.uow import UnitOfWork
from app.core.event_bus import event_bus

@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    async with session_factory() as session:
        # Start a nested transaction (savepoint) so we can roll back all writes
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
        is_platform_admin=True
    )
    
    # We create a dummy session factory that always returns our db_session
    class DummySessionFactory:
        def __call__(self):
            return db_session
            
    uow = UnitOfWork(
        session_factory=DummySessionFactory(),
        context=context,
        event_bus=event_bus,
        admin_session_factory=DummySessionFactory()
    )
    # Bind context for the duration of the test
    with bind_context(context):
        yield uow

@pytest_asyncio.fixture
async def client(db_session, test_uow):
    # Override get_db and get_uow to return our test database session and UoW
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_uow] = lambda: test_uow
    
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
        
    app.dependency_overrides.clear()
