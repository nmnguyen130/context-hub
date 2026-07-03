import json
import logging
import re
import unicodedata

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.clients import GeminiChatClient, GeminiEmbeddingClient
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.documents.models import Workspace
from app.modules.documents.retrieval import retrieve_grounding_chunks
from app.modules.documents.schemas import ChatRequest
from app.modules.documents.semantic_cache import SemanticCacheManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST endpoint for streaming grounded chat.
    Validates logical multi-tenancy, checks Redis Semantic Cache,
    retrieves hybrid grounding contexts, and streams syntheses with inline citations.
    """
    # 1. Validate logical multi-tenancy: verify workspace belongs to user's tenant
    stmt = select(Workspace).where(
        Workspace.id == request.workspace_id,
        Workspace.tenant_id == current_user.tenant_id,
    )
    workspace = (await db.execute(stmt)).scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found or access denied.",
        )

    # 2. Normalize query to Unicode NFC
    normalized_query = unicodedata.normalize("NFC", request.query)

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                cache_manager = SemanticCacheManager()
                embedding_client = GeminiEmbeddingClient(client=http_client)

                # 3. Generate query embedding vector
                query_vector = await embedding_client.get_embedding(normalized_query)

                # 4. Redis Semantic Cache VSS query hit check
                cached_answer = await cache_manager.get(query_vector)
                if cached_answer:
                    logger.info("Semantic cache HIT. Serving cached response.")
                    yield f"data: {json.dumps({'type': 'text', 'content': cached_answer})}\n\n"
                    yield 'data: {"type": "done"}\n\n'
                    return

                logger.info("Semantic cache MISS. Performing hybrid retrieval.")

                # 5. Perform Hybrid Search & Retrieval (Dense + Sparse + RRF + Rerank + Gate)
                chunks = await retrieve_grounding_chunks(
                    db,
                    current_user.tenant_id,
                    normalized_query,
                    query_vector=query_vector,
                    http_client=http_client,
                )

                # 6. Fallback if no grounding context passes relevance threshold gate
                if not chunks:
                    fallback_ans = "I cannot find the answer in the provided documents."
                    yield f"data: {json.dumps({'type': 'text', 'content': fallback_ans})}\n\n"
                    yield 'data: {"type": "done"}\n\n'
                    # Cache the fallback answer to save LLM hits
                    await cache_manager.set(
                        normalized_query, query_vector, fallback_ans
                    )
                    return

                # 7. Formulate Context Text and Citation map
                context_parts = []
                citations_map = []
                for idx, chunk in enumerate(chunks, 1):
                    chunk_id_str = str(chunk["id"])
                    citations_map.append(
                        {
                            "citation_index": idx,
                            "chunk_id": chunk_id_str,
                            "document_name": chunk["metadata"].get(
                                "document_name", "Unknown"
                            ),
                            "page_number": chunk["metadata"].get("page_number", 1),
                            "content": chunk["content"],
                        }
                    )
                    context_parts.append(
                        f"Source [{idx}] (ID: {chunk_id_str}):\n{chunk['content']}"
                    )

                context_text = "\n\n".join(context_parts)

                # 8. Define grounded assistant instructions
                system_instruction = (
                    "You are a grounded AI assistant for ContextHub.\n"
                    "Answer the user's question strictly using the provided Source facts.\n"
                    "Rules:\n"
                    "1. Do NOT infer, guess, or extrapolate. If the facts do not contain the answer, reply exactly: 'I cannot find the answer in the provided documents.'\n"
                    "2. Reference sources by appending [^[chunk_id]] inline (e.g., 'The system supports logical multi-tenancy [^[chunk_uuid_here]]').\n"
                    "Do not use normal footnotes or bracketed numbers like [1] for citations; use the exact [^[chunk_id]] format."
                )

                # 9. Stream Chat responses from Gemini Chat Client
                chat_client = GeminiChatClient(client=http_client)
                full_answer = ""
                prompt = f"Context:\n{context_text}\n\nQuery: {normalized_query}"
                async for text_chunk in chat_client.stream_chat(
                    prompt=prompt,
                    system_instruction=system_instruction,
                ):
                    full_answer += text_chunk
                    yield f"data: {json.dumps({'type': 'text', 'content': text_chunk})}\n\n"

            # 10. Extract citations and emit citation payload
            citation_uuids = re.findall(
                r"\[\^\[([a-f0-9\-]{36})\]\]", full_answer, re.IGNORECASE
            )
            unique_uuids = list(dict.fromkeys(citation_uuids))
            citations_dict = {c["chunk_id"]: c for c in citations_map}
            active_citations = []
            for uid in unique_uuids:
                match = citations_dict.get(uid)
                if match:
                    active_citations.append(match)

            yield f"data: {json.dumps({'type': 'citations', 'data': active_citations})}\n\n"
            yield 'data: {"type": "done"}\n\n'

            # 11. Write back to Redis Semantic Cache
            await cache_manager.set(normalized_query, query_vector, full_answer)

        except Exception as err:
            logger.error(f"Error in grounded chat stream: {str(err)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(err)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
