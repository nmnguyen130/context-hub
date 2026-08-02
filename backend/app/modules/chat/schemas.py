import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    workspace_id: uuid.UUID = Field(..., description="Target workspace ID")
    session_id: uuid.UUID | None = Field(
        default=None, description="Existing chat session ID (or null to start new)"
    )
    message: str = Field(
        ..., min_length=1, max_length=10000, description="User message query"
    )
    model: str | None = Field(
        default=None, description="Optional custom model override"
    )
    document_ids: list[uuid.UUID] | None = Field(
        default=None, description="Optional list of document IDs to scope search"
    )


class ChatSessionCreate(BaseModel):
    workspace_id: uuid.UUID
    title: str | None = Field(default=None, max_length=500)


class ChatSessionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    running_summary: str | None
    message_count: int
    total_tokens: int
    total_cost_usd: float
    created_at: datetime
    updated_at: datetime


class FeedbackRating(StrEnum):
    UP = "up"
    DOWN = "down"


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    citations: list[dict[str, Any]] | None = None
    confidence_score: float | None = None
    token_count: int
    cost_usd: float
    feedback: str | None = None
    feedback_note: str | None = None
    created_at: datetime


class ChatMessageFeedbackUpdate(BaseModel):
    feedback: FeedbackRating = Field(
        ..., description="Feedback rating e.g. 'up' or 'down'"
    )
    feedback_note: str | None = Field(
        default=None, max_length=2000, description="Optional feedback explanation note"
    )


class CitationDetail(BaseModel):
    index: int = Field(..., description="Citation marker number e.g. [^1]")
    document_id: uuid.UUID
    document_name: str
    chunk_id: uuid.UUID
    content_excerpt: str
    page_numbers: list[int] = Field(default_factory=list)
    confidence: float = 0.0


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


class SSEEvent(BaseModel):
    type: str = Field(
        ...,
        description="Event type: token, sources, citations, usage, done, or error",
    )
    data: Any = Field(..., description="Payload data for the event")
