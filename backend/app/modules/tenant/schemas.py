from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core.enums import DLPAction, PlanTier


class TenantSettings(BaseModel):
    """Tenant JSONB settings column schema."""

    model_config = ConfigDict(extra="forbid")
    dlp_enabled: bool = False
    dlp_action: DLPAction = DLPAction.MASK
    max_workspace_count: int = Field(default=10, ge=1, le=1000)
    custom_branding_logo_url: HttpUrl | None = None
    allowed_file_types: list[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".md", ".txt", ".csv"]
    )


class TenantSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dlp_enabled: bool | None = None
    dlp_action: DLPAction | None = None
    max_workspace_count: int | None = Field(default=None, ge=1, le=1000)
    custom_branding_logo_url: HttpUrl | None = None
    allowed_file_types: list[str] | None = None


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan_tier: PlanTier
    settings: TenantSettings
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=255)
    settings: TenantSettingsUpdate | None = None


class TenantResolveResponse(BaseModel):
    exists: bool
    name: str | None = None


class TenantStatsResponse(BaseModel):
    user_count: int
    document_count: int
    storage_used_bytes: int
