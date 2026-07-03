import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware import TenantContextMiddleware
from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Redis Semantic Cache VSS index on startup
    from app.modules.documents.semantic_cache import SemanticCacheManager

    cache_manager = SemanticCacheManager()
    await cache_manager.ensure_index()

    # 2. Startup Embedding Validation
    if settings.GEMINI_API_KEY:
        from app.core.clients import GeminiEmbeddingClient
        from app.modules.documents.models import DocumentChunk

        # Dynamically resolve dimension from SQLAlchemy model type definition
        db_dim = DocumentChunk.embedding.type.dim
        try:
            client = GeminiEmbeddingClient()
            vector = await client.get_embedding("startup_validation")
            returned_dim = len(vector)
            if returned_dim != db_dim:
                logger.critical(
                    f"Startup embedding dimension MISMATCH! "
                    f"Database expects {db_dim}, but API returned {returned_dim}."
                )
                raise ValueError("Embedding model dimension mismatch.")
            logger.info(
                f"Startup embedding validation passed. Dimension: {returned_dim}"
            )
        except Exception as e:
            logger.critical(f"Startup embedding validation FAILED: {str(e)}")
            raise e

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# 1. CORS Configuration
origins = [
    origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Multi-Tenancy Isolation Middleware
app.add_middleware(TenantContextMiddleware)


# 3. Healthcheck Router
@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Standard service health check endpoint.
    Performs ping operations on PostgreSQL and Redis to verify connection viability.
    """
    db_ok = False
    redis_ok = False

    # Check Database connection
    try:
        # Run a simple query utilizing the skip_tenant_filter execution option
        # since it's a global ping and does not run in a tenant context.
        await db.execute(text("SELECT 1").execution_options(skip_tenant_filter=True))
        db_ok = True
    except Exception:
        pass

    # Check Redis connection
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
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


# 4. API Core Router Registration
from app.api.router import api_router

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["System"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API Gateway",
        "docs_url": f"{settings.API_V1_STR}/docs",
    }
