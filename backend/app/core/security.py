import hashlib
import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings

_BCRYPT_MAX_BYTES = 72


def _truncate_pwd(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_truncate_pwd(password), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            _truncate_pwd(plain_password), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """SHA-256 hash a token for secure storage/lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: UUID, tenant_id: UUID, role: str, expires_delta: timedelta | None = None
) -> str:
    """Generates a signed JWT Access Token containing user claims."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "type": "access",
        "jti": uuid_mod.uuid4().hex,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: UUID, tenant_id: UUID, expires_delta: timedelta | None = None
) -> tuple[str, str, datetime]:
    """Generates a signed JWT Refresh Token. Returns (token_string, jti, expires_at)."""
    jti = uuid_mod.uuid4().hex
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "jti": jti,
        "exp": expires_at,
    }
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decodes and validates a JWT token, checking the type claim.

    Raises:
        jwt.PyJWTError: If the token is invalid or expired.
        ValueError: If the token type doesn't match expected_type.
    """
    payload = jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    if payload.get("type") != expected_type:
        raise ValueError(
            f"Expected token type '{expected_type}', got '{payload.get('type')}'"
        )
    return payload
