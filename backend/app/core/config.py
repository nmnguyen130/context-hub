from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: str = "development"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "contexthub"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
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

    # S3 / MinIO
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_BUCKET_NAME: str = "contexthub"
    S3_REGION_NAME: str | None = None
    S3_SECURE: bool = True
    MAX_FILE_SIZE_MB: int = 20

    # API Credentials
    GEMINI_API_KEY: str | None = None
    COHERE_API_KEY: str | None = None

    # RAG Pipeline
    RAG_EMBEDDING_MODEL: str = "gemini-embedding-001"
    RAG_CHAT_MODEL: str = "gemini-2.0-flash"
    RAG_RERANK_PROVIDER: str = "context_boost"

    # Search Thresholds & FTS
    RAG_FTS_LANGUAGE: str = "simple"
    RAG_LIMIT_DENSE: int = 50
    RAG_LIMIT_SPARSE: int = 50
    RAG_LIMIT_FUSED: int = 20
    RAG_FINAL_TOP_K: int = 5
    RAG_RELEVANCE_THRESHOLD: float = 0.05

    # Semantic Caching
    ENABLE_SEMANTIC_CACHE: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.95

    # Data Loss Prevention
    RAG_DLP_ACTION: str = "MASK"

    @model_validator(mode="after")
    def assemble_urls(self) -> "Settings":
        if self.DATABASE_URL is None:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        if self.REDIS_URL is None:
            self.REDIS_URL = (
                f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        if self.CELERY_BROKER_URL is None:
            self.CELERY_BROKER_URL = self.REDIS_URL
        return self

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.ALLOWED_ORIGINS == "*":
                raise ValueError(
                    "ALLOWED_ORIGINS cannot be '*' in production environment."
                )
            if len(self.JWT_SECRET) < 32:
                raise ValueError(
                    "JWT_SECRET must be at least 32 characters long in production."
                )
        return self


settings = Settings()
