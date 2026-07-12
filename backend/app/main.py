import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.middleware import RequestContextMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.database import async_session, engine
from app.core.exceptions import register_exception_handlers
from app.infrastructure.rate_limiter import LUA_SLIDING_WINDOW
from app.infrastructure.storage import S3StorageProvider
from app.utils.logging import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    app.state.storage = S3StorageProvider()

    # Preload rate limiter Lua script
    app.state.limiter_script = app.state.redis.register_script(LUA_SLIDING_WINDOW)

    yield

    # Teardown
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

register_exception_handlers(app)

# CORS Safety Validation
origins = [x.strip() for x in settings.ALLOWED_ORIGINS.split(",") if x.strip()]
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
async def health_check(request: Request):
    db_ok = False
    redis_ok = False

    # Check Database
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
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
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": f"{settings.API_V1_STR}/docs",
    }
