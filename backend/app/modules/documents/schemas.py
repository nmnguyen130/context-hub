from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """API response schema for Document model serialization."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    file_type: str
    object_store_key: str
    status: str
    file_size: int
    mime_type: str | None = None
    checksum: str | None = None
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
