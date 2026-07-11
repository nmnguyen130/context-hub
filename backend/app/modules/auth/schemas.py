from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.enums import InvitationStatus, UserRole


# Base
class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmailMixin(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.lower()


class NameMixin(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class PasswordMixin(BaseModel):
    password: str = Field(..., min_length=8, max_length=72)


# Registration
class RegisterRequest(EmailMixin, NameMixin, PasswordMixin):
    """Registration request schema."""

    tenant_name: str = Field(..., min_length=2, max_length=255)

    @field_validator("tenant_name")
    @classmethod
    def validate_tenant_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tenant name cannot be empty")
        return value


class JoinRequest(EmailMixin, NameMixin, PasswordMixin):
    """Join workspace request schema."""

    invite_token: str = Field(..., min_length=1)


# Authentication
class LoginRequest(EmailMixin):
    """Login request schema."""

    password: str = Field(..., min_length=1, max_length=72)
    tenant_slug: str = Field(..., min_length=1, max_length=255)

    @field_validator("tenant_slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# Invitations
class InvitationCreateRequest(EmailMixin):
    role: UserRole = UserRole.MEMBER


class InvitationResponse(ORMModel):
    id: UUID
    email: str
    role: UserRole
    status: InvitationStatus
    invited_by: UUID | None
    expires_at: datetime
    created_at: datetime


# User Management
class UserResponse(ORMModel):
    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    role: UserRole
    is_active: bool
    tenant_id: UUID
    last_login_at: datetime | None
    created_at: datetime


class UserUpdateRequest(NameMixin):
    """Profile update request schema."""


class UserRoleUpdateRequest(BaseModel):
    """Role update request schema."""

    role: UserRole


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=72)
    new_password: str = Field(..., min_length=8, max_length=72)
