# app/modules/chat/queries/stream_chat.py
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceError
from app.core.text_utils import normalize_text
from app.modules.chat.retrieval import retrieve_grounding_chunks
from app.modules.documents.models import Workspace

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "You are a grounded AI assistant for ContextHub.\n"
    "Answer the user's question strictly using the provided Source facts.\n"
    "Rules:\n"
    "1. Do NOT infer, guess, or extrapolate. If the facts do not contain the answer, "
    "reply exactly: 'I cannot find the answer in the provided documents.'\n"
    "2. Reference sources by appending [^[chunk_id]] inline (e.g., 'The system supports logical multi-tenancy [^[chunk_uuid_here]]').\n"
    "Do not use normal footnotes or bracketed numbers like [1] for citations; use the exact [^[chunk_id]] format."
)

FALLBACK_ANSWER = "I cannot find the answer in the provided documents."


@dataclass
class SSEEvent:
    event: str
    data: str


class StreamChatQuery:
    """Application Service (Query Use Case).

    Orchestrates RAG flow: cache validation -> retrieval -> LLM execution -> citation resolution.
    Yields structured SSE event dataclasses. Free of FastAPI HTTP dependencies.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedder: Any,
        chat: Any,
        cache: Any,
    ) -> None:
        self.db = db
        self.embedder = embedder
        self.chat = chat
        self.cache = cache

    async def validate(self, tenant_id: UUID, workspace_id: UUID) -> None:
        """Validates workspace existence and tenant permissions before stream initialization."""
        stmt = select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.tenant_id == tenant_id,
        )
        workspace = (await self.db.execute(stmt)).scalar_one_or_none()
        if not workspace:
            raise ServiceError("Workspace not found or access denied.", status_code=404)

    async def execute(
        self,
        query: str,
        tenant_id: UUID,
        workspace_id: UUID,
    ) -> AsyncGenerator[SSEEvent, None]:
        normalized_query = normalize_text(query)

        # 2. Generate embedding for semantic lookup
        query_vector = await self.embedder.get_embedding(normalized_query)

        # 3. Check semantic cache
        cached_answer = await self.cache.get(tenant_id, query_vector)
        if cached_answer:
            logger.info("Semantic cache HIT. Serving cached response.")
            yield SSEEvent(
                "message", json.dumps({"type": "text", "content": cached_answer})
            )
            yield SSEEvent("done", json.dumps({"type": "done"}))
            return

        logger.info("Semantic cache MISS. Performing hybrid retrieval.")

        # 4. Perform hybrid search (Dense + Sparse + RRF + Rerank + Relevance threshold)
        chunks = await retrieve_grounding_chunks(
            self.db,
            tenant_id,
            normalized_query,
            query_vector=query_vector,
        )

        # 5. Handle empty retrieval with fallback answer
        if not chunks:
            yield SSEEvent(
                "message", json.dumps({"type": "text", "content": FALLBACK_ANSWER})
            )
            yield SSEEvent("done", json.dumps({"type": "done"}))
            await self.cache.set(
                tenant_id, normalized_query, query_vector, FALLBACK_ANSWER
            )
            return

        # 6. Formulate context context details and citation map
        context_parts = []
        citations_map = {}
        for idx, chunk in enumerate(chunks, 1):
            chunk_id_str = str(chunk["id"])
            citations_map[chunk_id_str] = {
                "citation_index": idx,
                "chunk_id": chunk_id_str,
                "document_name": chunk["metadata"].get("document_name", "Unknown"),
                "page_number": chunk["metadata"].get("page_number", 1),
                "content": chunk["content"],
            }
            context_parts.append(
                f"Source [{idx}] (ID: {chunk_id_str}):\n{chunk['content']}"
            )

        prompt = f"Context:\n{r'\n\n'.join(context_parts)}\n\nQuery: {normalized_query}"

        # 7. Execute grounded LLM stream
        full_answer = ""
        async for token in self.chat.stream_chat(prompt, SYSTEM_INSTRUCTION):
            full_answer += token
            yield SSEEvent("token", json.dumps({"type": "text", "content": token}))

        # 8. Extract citations from response and return citation objects
        citation_uuids = list(
            dict.fromkeys(
                re.findall(r"\[\^\[([a-f0-9\-]{36})\]\]", full_answer, re.IGNORECASE)
            )
        )
        active_citations = [
            citations_map[uid] for uid in citation_uuids if uid in citations_map
        ]

        yield SSEEvent(
            "citations", json.dumps({"type": "citations", "data": active_citations})
        )
        yield SSEEvent("done", json.dumps({"type": "done"}))

        # 9. Populate semantic cache
        await self.cache.set(tenant_id, normalized_query, query_vector, full_answer)
