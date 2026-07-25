from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: str = "development"

    # Database
    POSTGRES_OWNER_USER: str = "postgres"
    POSTGRES_OWNER_PASSWORD: str

    POSTGRES_APP_USER: str = "contexthub_app"
    POSTGRES_APP_PASSWORD: str

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "contexthub"

    DATABASE_URL: str | None = None
    DATABASE_OWNER_URL: str | None = None

    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_OWNER_POOL_SIZE: int = 2

    # Redis / Worker
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ContextHub"
    ALLOWED_ORIGINS: str = "*"

    # Storage
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_BUCKET_NAME: str = "contexthub"
    S3_REGION_NAME: str = "us-east-1"
    S3_SECURE: bool = True
    MAX_FILE_SIZE_MB: int = 20

    # AI Providers
    GEMINI_API_KEY: str | None = None
    COHERE_API_KEY: str | None = None

    # RAG
    RAG_EMBEDDING_MODEL: str = "gemini-embedding-001"
    RAG_EMBEDDING_DIMENSION: int = 768
    RAG_CHAT_MODEL: str = "gemini-2.0-flash"
    RAG_FINAL_TOP_K: int = 5
    RAG_RELEVANCE_THRESHOLD: float = 0.05
    RAG_RRF_K: int = 60
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 100
    RAG_MEMORY_WINDOW: int = 6
    RAG_SESSION_CACHE_TTL: int = 300
    RAG_SEMANTIC_CACHE_TTL: int = 3600
    RAG_HYDE_CHUNK_THRESHOLD: int = 500
    RAG_ALLOWED_EXTENSIONS: str = ".pdf,.docx,.md,.txt,.csv,.json"
    RAG_CRAG_RETRY_ENABLED: bool = True

    # Cache
    ENABLE_SEMANTIC_CACHE: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.95

    # Security pipeline
    RAG_DLP_ACTION: str = "MASK"

    @model_validator(mode="after")
    def validate_settings(self):
        if self.DATABASE_URL is None:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_APP_USER}:{self.POSTGRES_APP_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if self.DATABASE_OWNER_URL is None:
            self.DATABASE_OWNER_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_OWNER_USER}:{self.POSTGRES_OWNER_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        if self.CELERY_BROKER_URL is None:
            self.CELERY_BROKER_URL = self.REDIS_URL

        if self.ENVIRONMENT == "production":
            if self.ALLOWED_ORIGINS == "*":
                raise ValueError("ALLOWED_ORIGINS cannot be '*' in production")

            if len(self.JWT_SECRET) < 32:
                raise ValueError("JWT_SECRET must have at least 32 characters")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
