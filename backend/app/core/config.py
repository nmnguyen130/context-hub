from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: str = Field(default="development")

    # Database Configuration
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str  # Required field, must be set in environment
    POSTGRES_DB: str = Field(default="contexthub")

    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)

    DATABASE_URL: str | None = Field(default=None)
    REDIS_URL: str | None = Field(default=None)
    CELERY_BROKER_URL: str | None = Field(default=None)

    # Security Configuration
    JWT_SECRET: str  # Required field, must be set in environment
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)  # 1 day

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ContextHub"
    ALLOWED_ORIGINS: str = Field(default="*")

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


settings = Settings()
