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
    """Fetch recent messages for a chat session in chronological order."""
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)
    if tenant_id is not None:
        stmt = stmt.where(ChatMessage.tenant_id == tenant_id)

    stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)
    res = await session.scalars(stmt)
    return list(reversed(res.all()))


def format_history_for_prompt(
    messages: list[ChatMessage],
    max_words: int = 100,
) -> list[str]:
    """Format messages, keeping past assistant responses concise by word boundary."""
    formatted = []
    for msg in messages:
        words = msg.content.split()
        if msg.role == "assistant" and len(words) > max_words:
            content = " ".join(words[:max_words])
        else:
            content = msg.content
        formatted.append(f"{msg.role}: {content}")
    return formatted
