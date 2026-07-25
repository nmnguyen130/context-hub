"""SQLAlchemy models for chat sessions and messages."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import TenantBaseModel


class ChatSession(TenantBaseModel):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index(
            "ix_chat_sessions_user_workspace", "tenant_id", "user_id", "workspace_id"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    running_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(TenantBaseModel):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    retrieved_chunks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
