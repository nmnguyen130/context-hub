import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings
from app.core.context import UserRole

_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_password_bytes(password), salt).decode()


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verifies a password against a hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(plain_password), hashed_password.encode())
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """SHA-256 hashes a token."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: UUID, tenant_id: UUID, role: UserRole) -> str:
    """Creates a signed JWT access token."""
    expires = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role.value,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "exp": expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID, tenant_id: UUID) -> tuple[str, str, datetime]:
    """Creates a signed JWT refresh token."""
    jti = uuid.uuid4().hex
    expires = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "jti": jti,
        "exp": expires,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decodes and validates a JWT token."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={
            "require": ["exp", "type"],
        },
    )
    if payload.get("type") != expected_type:
        raise ValueError(
            f"Expected token type '{expected_type}', got '{payload.get('type')}'"
        )
    return payload
