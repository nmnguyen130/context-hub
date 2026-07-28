import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.documents.models import DocumentStatus


@dataclass
class ScoredChunk:
    """Dataclass representing a text chunk with relevance scores."""

    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    metadata: dict
    cosine_score: float = 0.0
    fts_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    dlp_rules: dict | None = None
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    content_hash: str
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str = "Document uploaded and queued for processing."
