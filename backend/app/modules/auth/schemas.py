import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Standard robust email regex pattern
EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"


class AuthBase(BaseModel):
    email: str = Field(..., max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("Invalid email format")
        return v


class UserRegister(AuthBase):
    """Schema for registering a new tenant organization and its Administrator user."""

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


class UserJoin(AuthBase):
    """Schema for an employee registering to join an existing tenant using a signed invite token."""

    password: str = Field(..., min_length=8, max_length=72)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    invite_token: str = Field(...)


class UserLogin(AuthBase):
    """Schema for local credentials login."""

    password: str = Field(..., min_length=1, max_length=72)


class Token(BaseModel):
    """Response schema containing access token and token type."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user profile serialization schema."""

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    role: str
    tenant_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
