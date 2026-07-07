import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = r"^[\w\.\+\-]+@[\w\.\-]+\.\w+$"


# ============================================================
# Base
# ============================================================
class _EmailMixin(BaseModel):
    email: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("Invalid email format")
        return v


# ============================================================
# Registration
# ============================================================
class RegisterRequest(_EmailMixin):
    """Register a new tenant organization + admin user."""

    password: str = Field(..., min_length=8, max_length=72)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    tenant_name: str = Field(..., min_length=2, max_length=255)

    @field_validator("tenant_name")
    @classmethod
    def validate_tenant_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Tenant name cannot be empty")
        return v


class JoinRequest(_EmailMixin):
    """Join an existing tenant via invitation token."""

    password: str = Field(..., min_length=8, max_length=72)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    invite_token: str


# ============================================================
# Authentication
# ============================================================
class LoginRequest(_EmailMixin):
    """Login with email + password + tenant slug."""

    password: str = Field(..., min_length=1, max_length=72)
    tenant_slug: str = Field(..., min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expiry


# ============================================================
# Invitations
# ============================================================
class InviteCreateRequest(_EmailMixin):
    role: str = Field(default="MEMBER", pattern="^(MEMBER|VIEWER)$")


class InviteResponse(BaseModel):
    id: UUID
    email: str
    role: str
    status: str
    invited_by: UUID | None
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# User Management
# ============================================================
class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    role: str
    is_active: bool
    tenant_id: UUID
    last_login_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Self-service profile update."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class UserRoleUpdateRequest(BaseModel):
    """Admin-only role change."""

    role: str = Field(..., pattern="^(ADMIN|MEMBER|VIEWER)$")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=72)
    new_password: str = Field(..., min_length=8, max_length=72)
