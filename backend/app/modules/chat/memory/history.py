import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.models import ChatMessage


async def get_recent_messages(
    session: AsyncSession,
    session_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
    limit: int = 6,
) -> list[ChatMessage]:
    """Fetch the most recent `limit` messages for a chat session in chronological order."""
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)
    if tenant_id is not None:
        stmt = stmt.where(ChatMessage.tenant_id == tenant_id)

    stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)
    res = await session.scalars(stmt)
    # Reverse so returned list is chronological (oldest to newest)
    return list(reversed(res.all()))


def format_history_for_prompt(messages: list[ChatMessage]) -> list[str]:
    """Format messages into a list of strings 'role: content' for LLM query rewriting."""
    return [f"{msg.role}: {msg.content}" for msg in messages]
