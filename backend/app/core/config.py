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

    DATABASE_URL: str | None = None

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
    S3_SECURE: bool = True
    MAX_FILE_SIZE_MB: int = 20

    # AI Providers
    GEMINI_API_KEY: str | None = None
    COHERE_API_KEY: str | None = None

    # RAG
    RAG_EMBEDDING_MODEL: str = "gemini-embedding-001"
    RAG_CHAT_MODEL: str = "gemini-2.0-flash"
    RAG_FINAL_TOP_K: int = 5
    RAG_RELEVANCE_THRESHOLD: float = 0.05

    # Cache
    ENABLE_SEMANTIC_CACHE: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.95

    # Security pipeline
    RAG_DLP_ACTION: str = "MASK"

    @model_validator(mode="after")
    def validate_settings(self):
        if self.DATABASE_URL is None:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
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


settings = Settings()
