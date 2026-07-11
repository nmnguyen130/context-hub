# app/modules/chat/router.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.api.deps import RAGContainer, get_current_user, get_infra, get_uow
from app.core.uow import UnitOfWork
from app.core.events import DomainEvent
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
    uow: UnitOfWork = Depends(get_uow),
) -> StreamingResponse:
    """POST endpoint for streaming grounded chat."""
    embedder = infra.get_embedding_client(provider="gemini")
    chat = infra.get_chat_client(provider="gemini")
    cache = infra.get_cache()

    # Pass uow.session to query
    query = StreamChatQuery(uow.session, embedder, chat, cache)
    await query.validate(current_user.tenant_id, body.workspace_id)

    async def event_generator():
        async for event in query.execute(
            body.query, current_user.tenant_id, body.workspace_id
        ):
            if await request_obj.is_disconnected():
                break
            yield f"data: {event.data}\n\n"

        # Record chat completion event after streaming finishes
        uow.record_event(DomainEvent(
            event_type="chat.query_completed",
            payload={
                "tenant_id": str(current_user.tenant_id),
                "user_id": str(current_user.id),
                "workspace_id": str(body.workspace_id),
                "query": body.query
            }
        ))
        await uow.commit()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
