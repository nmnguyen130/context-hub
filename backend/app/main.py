import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Setup Logging Early
from app.core.logging import setup_logging

setup_logging()

from app.api.deps import get_db
from app.api.middleware import RequestContextMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.database import Database
from app.core.exceptions import register_exception_handlers
from app.core.limiter import LUA_SLIDING_WINDOW
from app.core.storage import S3StorageProvider

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = Database(settings.DATABASE_URL)
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    app.state.storage = S3StorageProvider()

    # Preload rate limiter Lua script
    app.state.limiter_script = app.state.redis.register_script(LUA_SLIDING_WINDOW)

    try:
        await app.state.storage.ensure_bucket_exists()
    except Exception:
        logger.warning("S3 bucket check failed on startup")

    # Embedding dimension validation
    if settings.GEMINI_API_KEY:
        from app.infrastructure.clients import GeminiEmbeddingClient
        from app.modules.documents.models import DocumentChunk

        db_dim = DocumentChunk.embedding.type.dim
        try:
            client = GeminiEmbeddingClient()
            vector = await client.get_embedding("startup_validation")
            if (dim := len(vector)) != db_dim:
                raise ValueError(f"Dimension mismatch: expected {db_dim}, got {dim}")
            logger.info(f"Embedding validation passed (dim={db_dim})")
        except Exception as e:
            logger.critical(f"Embedding validation failed: {e}")
            raise

    # Start outbox relay background task
    import asyncio
    from app.worker.outbox_relay import relay_loop
    from app.core.event_bus import event_bus
    relay_task = asyncio.create_task(
        relay_loop(
            session_factory=app.state.db.session_factory,
            event_bus=event_bus,
            poll_interval=0.5
        )
    )

    yield

    # Teardown
    relay_task.cancel()
    try:
        await relay_task
    except asyncio.CancelledError:
        pass

    await app.state.redis.aclose()
    await app.state.db.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

register_exception_handlers(app)

# CORS Safety Validation
origins = [
    origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()
]
if "*" in origins:
    if settings.ENVIRONMENT == "production":
        raise ValueError(
            "CORS allow_origins cannot contain '*' in production environment."
        )
    logger.warning(
        "CORS allow_origins contains '*' with credentials enabled. This is insecure."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Multi-Tenancy Isolation & Tracing
app.add_middleware(RequestContextMiddleware)


# Healthcheck
@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """Service health check (pings Postgres and Redis)."""
    db_ok = False
    redis_ok = False

    # Check Database
    try:
        await db.execute(text("SELECT 1").execution_options(skip_tenant_filter=True))
        db_ok = True
    except Exception:
        pass

    # Check Redis
    try:
        redis_client = request.app.state.redis
        await redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    overall_status = "healthy" if (db_ok and redis_ok) else "degraded"

    return {
        "status": overall_status,
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": "reachable" if db_ok else "unreachable",
            "redis": "reachable" if redis_ok else "unreachable",
        },
    }


# Routing
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["System"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API Gateway",
        "docs_url": f"{settings.API_V1_STR}/docs",
    }
