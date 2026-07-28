import logging
import uuid

from sqlalchemy import func, select

from app.core.clients import GeminiClient
from app.core.context import try_current_context
from app.core.exceptions import ServiceError
from app.core.pagination import PaginationParams
from app.core.uow import UnitOfWork
from app.modules.chat.exceptions import ChatSessionNotFoundError
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.chat.schemas import ChatSessionCreate, ChatSessionUpdate
from app.modules.documents.models import Workspace

logger = logging.getLogger(__name__)


class ChatSessionService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create(self, data: ChatSessionCreate) -> ChatSession:
        """Create a new chat session for the given workspace."""
        ctx = try_current_context()
        if not ctx or not ctx.tenant_id or not ctx.user_id:
            raise ServiceError("Tenant and User context required", status_code=400)

        workspace = await self.uow.session.get(Workspace, data.workspace_id)
        if workspace is None or workspace.tenant_id != ctx.tenant_id:
            raise ServiceError("Workspace not found", status_code=404)

        session = ChatSession(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            workspace_id=data.workspace_id,
            title=data.title or "New Conversation",
        )
        self.uow.session.add(session)
        await self.uow.flush()
        return session

    async def get(
        self, session_id: uuid.UUID, require_owner: bool = False
    ) -> ChatSession:
        """Retrieve a chat session by ID with tenant and optional user ownership validation."""
        ctx = try_current_context()
        session = await self.uow.session.get(ChatSession, session_id)
        if session is None:
            raise ChatSessionNotFoundError()

        if ctx and ctx.tenant_id and session.tenant_id != ctx.tenant_id:
            raise ChatSessionNotFoundError()

        if require_owner and ctx and ctx.user_id and session.user_id != ctx.user_id:
            raise ChatSessionNotFoundError()

        return session

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[ChatSession], int]:
        """List active chat sessions belonging to a workspace for current tenant/user."""
        pagination = pagination or PaginationParams()
        ctx = try_current_context()
        if not ctx or not ctx.tenant_id or not ctx.user_id:
            raise ServiceError("Tenant and User context required", status_code=400)

        stmt = (
            select(ChatSession)
            .where(
                ChatSession.tenant_id == ctx.tenant_id,
                ChatSession.workspace_id == workspace_id,
                ChatSession.user_id == ctx.user_id,
            )
            .order_by(ChatSession.updated_at.desc())
        )

        total = (
            await self.uow.session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            or 0
        )
        items = (
            await self.uow.session.scalars(
                stmt.offset(pagination.offset).limit(pagination.limit)
            )
        ).all()
        return list(items), total

    async def update(
        self, session_id: uuid.UUID, data: ChatSessionUpdate
    ) -> ChatSession:
        """Update chat session details (e.g. title)."""
        session = await self.get(session_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(session, key, value)
        await self.uow.flush()
        return session

    async def delete(self, session_id: uuid.UUID) -> None:
        """Delete a chat session and all its messages."""
        session = await self.get(session_id)
        await self.uow.session.delete(session)
        await self.uow.flush()

    async def list_messages(
        self,
        session_id: uuid.UUID,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[ChatMessage], int]:
        """List messages for a chat session with pagination."""
        pagination = pagination or PaginationParams()
        await self.get(session_id)  # validate session exists and tenant matches

        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )

        total = (
            await self.uow.session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            or 0
        )
        items = (
            await self.uow.session.scalars(
                stmt.offset(pagination.offset).limit(pagination.limit)
            )
        ).all()
        return list(items), total

    async def set_message_feedback(
        self,
        message_id: uuid.UUID,
        feedback: str,
        feedback_note: str | None = None,
    ) -> ChatMessage:
        """Set user feedback rating (up/down) and optional note for a message."""
        ctx = try_current_context()
        message = await self.uow.session.get(ChatMessage, message_id)
        if message is None:
            raise ServiceError("Message not found", status_code=404)

        if ctx and ctx.tenant_id and message.tenant_id != ctx.tenant_id:
            raise ServiceError("Message not found", status_code=404)

        message.feedback = feedback
        message.feedback_note = feedback_note
        await self.uow.flush()
        return message

    async def auto_title(
        self,
        session_id: uuid.UUID,
        first_message: str,
        client: GeminiClient | None = None,
    ) -> str:
        """Generate a concise title for a session from the first user message."""
        session = await self.get(session_id)
        client = client or GeminiClient()
        prompt = (
            "Generate a concise 3-6 word title summarizing this initial user query. "
            "Output ONLY the title string, without quotes or formatting.\n\n"
            f"Query: {first_message}"
        )
        try:
            title = (
                (await client.generate(prompt, temperature=0.3)).strip().strip("\"'")
            )
            if title:
                session.title = title[:200]
                await self.uow.flush()
                return session.title
        except Exception as exc:
            logger.warning("Auto-titling LLM call failed: %s", exc)

        fallback = first_message[:50] + ("..." if len(first_message) > 50 else "")
        session.title = fallback
        await self.uow.flush()
        return fallback

    async def update_summary(
        self,
        session_id: uuid.UUID,
        messages: list[ChatMessage],
        client: GeminiClient | None = None,
    ) -> str | None:
        """Incrementally update the rolling summary of the conversation."""
        session = await self.get(session_id)
        client = client or GeminiClient()
        history_str = "\n".join([f"{m.role}: {m.content}" for m in messages[-6:]])

        prompt = (
            "Summarize the key context and user intentions from this conversation segment in 2-3 concise sentences. "
            f"Previous Summary: {session.running_summary or 'None'}\n\n"
            f"Recent Messages:\n{history_str}\n\nNew Summary:"
        )
        try:
            new_summary = (await client.generate(prompt, temperature=0.2)).strip()
            session.running_summary = new_summary
            await self.uow.flush()
            return new_summary
        except Exception as exc:
            logger.warning("Summary update LLM call failed: %s", exc)
            return session.running_summary
