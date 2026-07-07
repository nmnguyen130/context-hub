from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import RAGContainer, get_current_user, get_infra
from app.modules.auth.models import User
from app.modules.chat.queries.stream_chat import StreamChatQuery
from app.modules.chat.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/stream")
async def chat_stream(
    request_obj: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    infra: RAGContainer = Depends(get_infra),
) -> StreamingResponse:
    """POST endpoint for streaming grounded chat.

    Delegates RAG query logic to StreamChatQuery use case.
    Handles SSE streaming format and client disconnect detection.

    Args:
        request_obj (Request): Client connection details.
        body (ChatRequest): Incoming chat request data.
        current_user (User): Current authenticated user.
        infra (RAGContainer): Infrastructure registry container.

    Returns:
        StreamingResponse: SSE stream response.
    """
    embedder = infra.get_embedding_client(provider="gemini")
    chat = infra.get_chat_client(provider="gemini")
    cache = infra.get_cache()

    query = StreamChatQuery(infra.db, embedder, chat, cache)
    await query.validate(current_user.tenant_id, body.workspace_id)

    async def event_generator():
        async for event in query.execute(
            body.query, current_user.tenant_id, body.workspace_id
        ):
            if await request_obj.is_disconnected():
                break
            yield f"data: {event.data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
