import logging
import uuid

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_authenticated_context, get_service
from app.core.context import RequestContext
from app.core.exceptions import ServiceError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.modules.chat.memory import ChatSessionService
from app.modules.chat.schemas import (
    ChatMessageResponse,
    ChatRequest,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
    SSEEvent,
)
from app.modules.chat.services import ChatService

logger = logging.getLogger(__name__)

chat_router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
    dependencies=[Depends(get_authenticated_context)],
)


@chat_router.post(
    "/stream",
    summary="Stream grounded RAG chat response",
    description="Stream tokens and metadata citations via Server-Sent Events (SSE).",
)
async def stream_chat(
    request: Request,
    body: ChatRequest,
    context: RequestContext = Depends(get_authenticated_context),
    service: ChatService = Depends(get_service(ChatService)),
):
    """Stream a grounded RAG conversation response with citations via SSE."""

    async def event_generator():
        try:
            async for event in service.process_query(body, context):
                yield f"data: {event.model_dump_json()}\n\n"
                if await request.is_disconnected():
                    break
            else:
                yield "data: [DONE]\n\n"
        except ServiceError as exc:
            event = SSEEvent(type="error", data={"message": exc.detail})
            yield f"data: {event.model_dump_json()}\n\n"
        except Exception:
            logger.exception("Chat stream failed")
            event = SSEEvent(
                type="error",
                data={
                    "message": "An unexpected error occurred while processing your chat request."
                },
            )
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    data: ChatSessionCreate,
    service: ChatSessionService = Depends(get_service(ChatSessionService)),
):
    """Create a new chat session in a workspace."""
    session = await service.create(data)
    await service.uow.commit()
    return session


@chat_router.get(
    "/sessions/workspace/{workspace_id}",
    response_model=PaginatedResponse[ChatSessionResponse],
)
async def list_sessions(
    workspace_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    service: ChatSessionService = Depends(get_service(ChatSessionService)),
):
    """List all chat sessions in a workspace for the current user."""
    items, total = await service.list_by_workspace(workspace_id, pagination)
    return PaginatedResponse.create(items, total, pagination)


@chat_router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
)
async def get_session(
    session_id: uuid.UUID,
    service: ChatSessionService = Depends(get_service(ChatSessionService)),
):
    """Retrieve a single chat session by ID."""
    return await service.get(session_id)


@chat_router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
)
async def update_session(
    session_id: uuid.UUID,
    data: ChatSessionUpdate,
    service: ChatSessionService = Depends(get_service(ChatSessionService)),
):
    """Update a chat session title."""
    session = await service.update(session_id, data)
    await service.uow.commit()
    return session


@chat_router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: uuid.UUID,
    service: ChatSessionService = Depends(get_service(ChatSessionService)),
):
    """Delete a chat session and all its messages."""
    await service.delete(session_id)
    await service.uow.commit()


@chat_router.get(
    "/sessions/{session_id}/messages",
    response_model=PaginatedResponse[ChatMessageResponse],
)
async def list_messages(
    session_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    service: ChatSessionService = Depends(get_service(ChatSessionService)),
):
    """List message history for a chat session with pagination."""
    items, total = await service.list_messages(session_id, pagination)
    return PaginatedResponse.create(items, total, pagination)
