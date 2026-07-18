import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.unit
def test_production_rejects_wildcard_origins():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            ALLOWED_ORIGINS="*",
            POSTGRES_PASSWORD="pass",
            JWT_SECRET="too-short-secret-less-than-thirty-two-chars",
        )


@pytest.mark.unit
def test_production_requires_long_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            ALLOWED_ORIGINS="https://contexthub.com",
            POSTGRES_PASSWORD="pass",
            JWT_SECRET="short-secret",
        )


@pytest.mark.unit
def test_database_url_auto_builds():
    settings = Settings(
        POSTGRES_USER="testuser",
        POSTGRES_PASSWORD="testpassword",
        POSTGRES_HOST="testhost",
        POSTGRES_PORT=9999,
        POSTGRES_DB="testdb",
        JWT_SECRET="abcdefghijklmnopqrstuvwxyz1234567890",
    )
    assert (
        settings.DATABASE_URL
        == "postgresql+asyncpg://testuser:testpassword@testhost:9999/testdb"
    )
