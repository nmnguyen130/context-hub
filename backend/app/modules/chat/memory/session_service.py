import logging
from uuid import UUID

from sqlalchemy import delete, select

from app.core.clients import GeminiClient
from app.core.exceptions import ServiceError
from app.core.pagination import CursorParams, paginate_cursor
from app.core.uow import UnitOfWork
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.chat.schemas import ChatSessionCreate, ChatSessionUpdate
from app.modules.documents.models import Workspace

logger = logging.getLogger(__name__)


class ChatSessionService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create(
        self, tenant_id: UUID, user_id: UUID, data: ChatSessionCreate
    ) -> ChatSession:
        """Create a new chat session for the given workspace."""
        workspace = await self.uow.session.get(Workspace, data.workspace_id)
        if (
            workspace is None
            or workspace.tenant_id != tenant_id
            or not workspace.is_active
        ):
            raise ServiceError.not_found("Workspace")

        return await self.create_for_workspace(
            tenant_id=tenant_id,
            user_id=user_id,
            workspace=workspace,
            title=data.title,
        )

    async def create_for_workspace(
        self,
        tenant_id: UUID,
        user_id: UUID,
        workspace: Workspace,
        title: str | None = None,
    ) -> ChatSession:
        """Create a session directly from a validated workspace object without redundant lookup."""
        session = ChatSession(
            tenant_id=tenant_id,
            user_id=user_id,
            workspace_id=workspace.id,
            title=title or "New Conversation",
        )
        self.uow.session.add(session)
        await self.uow.flush()
        return session

    async def get(
        self, tenant_id: UUID, session_id: UUID, user_id: UUID | None = None
    ) -> ChatSession:
        """Retrieve a chat session by ID with tenant and optional user ownership validation."""
        session = await self.uow.session.get(ChatSession, session_id)
        if session is None or session.tenant_id != tenant_id:
            raise ServiceError.not_found("Chat session")

        if user_id and session.user_id != user_id:
            raise ServiceError.not_found("Chat session")

        return session

    async def list_by_workspace(
        self,
        tenant_id: UUID,
        user_id: UUID,
        workspace_id: UUID,
        params: CursorParams | None = None,
    ) -> tuple[list[ChatSession], str | None, bool]:
        """List active chat sessions belonging to a workspace with pagination."""
        params = params or CursorParams()
        stmt = select(ChatSession).where(
            ChatSession.tenant_id == tenant_id,
            ChatSession.workspace_id == workspace_id,
            ChatSession.user_id == user_id,
        )
        return await paginate_cursor(
            self.uow.session,
            stmt,
            params,
            sort_column=ChatSession.updated_at,
            id_column=ChatSession.id,
        )

    async def update(
        self, tenant_id: UUID, session_id: UUID, data: ChatSessionUpdate
    ) -> ChatSession:
        """Update chat session details (e.g. title)."""
        session = await self.get(tenant_id, session_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(session, key, value)
        await self.uow.flush()
        return session

    async def delete(self, tenant_id: UUID, session_id: UUID) -> None:
        """Delete a chat session and all its messages."""
        stmt = delete(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.tenant_id == tenant_id,
        )
        res = await self.uow.session.execute(stmt)
        if res.rowcount == 0:
            raise ServiceError.not_found("Chat session")
        await self.uow.flush()

    async def list_messages(
        self,
        tenant_id: UUID,
        session_id: UUID,
        params: CursorParams | None = None,
    ) -> tuple[list[ChatMessage], str | None, bool]:
        """List messages for a chat session with pagination in chronological order."""
        params = params or CursorParams()
        stmt = select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.tenant_id == tenant_id,
        )
        return await paginate_cursor(
            self.uow.session,
            stmt,
            params,
            sort_column=ChatMessage.created_at,
            id_column=ChatMessage.id,
            ascending=True,
        )

    async def set_message_feedback(
        self,
        tenant_id: UUID,
        message_id: UUID,
        feedback: str,
        feedback_note: str | None = None,
    ) -> ChatMessage:
        """Set user feedback rating (up/down) and optional note for a message."""
        message = await self.uow.session.get(ChatMessage, message_id)
        if message is None or message.tenant_id != tenant_id:
            raise ServiceError.not_found("Message")

        message.feedback = feedback
        message.feedback_note = feedback_note
        await self.uow.flush()
        return message

    async def auto_title(
        self,
        session: ChatSession,
        first_message: str,
        client: GeminiClient | None = None,
    ) -> str:
        """Generate a concise title for a session from the first user message."""
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
        session: ChatSession,
        messages: list[ChatMessage],
        client: GeminiClient | None = None,
    ) -> str | None:
        """Incrementally update the rolling summary of the conversation."""
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
