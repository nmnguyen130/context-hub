from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt.
    Enforces maximum password length of 72 bytes to prevent bcrypt ValueErrors.
    """
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        # Truncate to 72 bytes explicitly as required by bcrypt 4.0.0
        pwd_bytes = pwd_bytes[:72]

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """
    Verifies a plain password against a bcrypt hash in constant time.
    Returns False if password_hash is not set (e.g., SSO users).
    """
    if not hashed_password:
        return False

    pwd_bytes = plain_password.encode("utf-8")
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]

    hashed_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except ValueError:
        # Invalid hash format
        return False


def create_access_token(
    user_id: UUID, tenant_id: UUID, role: str, expires_delta: timedelta | None = None
) -> str:
    """
    Generates a secure signed JWT Access Token containing user claims.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_invite_token(
    tenant_id: UUID, email: str, role: str = "MEMBER", expires_in_days: int = 7
) -> str:
    """
    Generates a signed JWT invitation token to join an existing organization.
    Ensures safe enterprise onboarding.
    """
    expire = datetime.now(UTC) + timedelta(days=expires_in_days)
    to_encode = {
        "invite_tenant_id": str(tenant_id),
        "invite_email": email.lower(),
        "invite_role": role,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_invite_token(token: str) -> dict | None:
    """
    Decodes and validates a signed invitation token.
    Returns decoded claims if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        # Verify it is an invite token
        if "invite_tenant_id" in payload and "invite_email" in payload:
            return payload
    except jwt.PyJWTError:
        pass
    return None
