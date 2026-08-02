import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.tenant.models import PlanTier

SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is not None:
            val = v.strip().lower()
            if not SLUG_REGEX.match(val):
                raise ValueError(
                    "Slug must contain only lowercase letters, numbers, and single hyphens (no spaces, leading/trailing hyphens)."
                )
            return val
        return v


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    settings: dict | None = None


class TenantLookupResponse(BaseModel):
    exists: bool
    name: str | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    plan_tier: PlanTier
    settings: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TenantStatsResponse(BaseModel):
    user_count: int
    document_count: int
    storage_used_bytes: int
