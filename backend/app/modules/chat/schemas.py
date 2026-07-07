# app/modules/chat/schemas.py
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., max_length=2000, description="User query for chat session")
    workspace_id: UUID
