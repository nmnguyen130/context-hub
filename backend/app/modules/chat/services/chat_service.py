import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis

from app.core.clients import CohereClient, GeminiClient
from app.core.config import settings
from app.core.context import RequestContext
from app.core.uow import UnitOfWork
from app.modules.chat.cache.semantic_cache import SemanticCache
from app.modules.chat.generation import stream_synthesis
from app.modules.chat.memory import (
    ChatSessionService,
    format_history_for_prompt,
    get_recent_messages,
)
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.chat.query import QueryComplexity, prepare_queries
from app.modules.chat.query.rewriter import rewrite_query
from app.modules.chat.retrieval import Reranker, retrieve_context
from app.modules.chat.schemas import ChatRequest, ChatSessionCreate, SSEEvent
from app.modules.documents.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        uow: UnitOfWork,
        redis_client: aioredis.Redis | None = None,
        gemini_client: GeminiClient | None = None,
        cohere_client: CohereClient | None = None,
    ) -> None:
        self.uow = uow
        self.gemini_client = gemini_client or GeminiClient()
        self.embedder = EmbeddingProvider(client=self.gemini_client)
        self.reranker = Reranker(cohere_client=cohere_client or CohereClient())
        self.cache = SemanticCache(redis_client=redis_client)
        self.session_service = ChatSessionService(uow=self.uow)

    async def process_query(
        self,
        request: ChatRequest,
        context: RequestContext,
    ) -> AsyncIterator[SSEEvent]:
        """Full end-to-end RAG workflow: resolve session -> cache check -> query plan -> retrieval -> CRAG -> stream synthesis -> persist."""
        # 1. Resolve or create chat session
        session = await self._resolve_session(request, context)

        # Emit session metadata event
        yield SSEEvent(
            type="session",
            data={
                "session_id": str(session.id),
                "title": session.title,
                "workspace_id": str(session.workspace_id),
            },
        )

        # 2. Get history messages
        history_messages = await get_recent_messages(
            session=self.uow.session,
            session_id=session.id,
            tenant_id=context.tenant_id,
            limit=settings.RAG_MEMORY_WINDOW,
        )
        history_texts = format_history_for_prompt(history_messages)

        # 3. Check Semantic Cache (only for fresh single-turn queries)
        query_embedding: list[float] | None = None
        if not history_texts and settings.ENABLE_SEMANTIC_CACHE:
            try:
                query_embedding = await self.embedder.embed_query(request.message)
                cached = await self.cache.get(query_embedding, request.workspace_id)
                if cached:
                    yield SSEEvent(type="sources", data=cached.get("citations", []))
                    yield SSEEvent(type="token", data={"text": cached["content"]})
                    yield SSEEvent(type="citations", data=cached.get("citations", []))
                    yield SSEEvent(
                        type="done",
                        data={
                            "full_text": cached["content"],
                            "cached": True,
                            "similarity": cached.get("similarity"),
                        },
                    )

                    await self._persist_messages(
                        session=session,
                        user_query=request.message,
                        assistant_response=cached["content"],
                        citations=cached.get("citations", []),
                        retrieved_chunk_ids=[],
                        context=context,
                    )
                    return
            except Exception as exc:
                logger.warning("Semantic cache check failed: %s", exc)

        # 4. Adaptive Query Understanding Pipeline
        query_plan = await prepare_queries(
            query=request.message,
            history=history_texts,
            client=self.gemini_client,
            embedder=self.embedder,
        )

        # 5. Hybrid Retrieval + RRF + Reranking + CRAG Grading
        retrieval = await retrieve_context(
            query_plan=query_plan,
            workspace_ids=[request.workspace_id],
            tenant_id=context.tenant_id,
            session=self.uow.session,
            reranker=self.reranker,
            original_query=request.message,
        )

        # 6. Corrective RAG (CRAG) Retry logic on low confidence
        if (
            retrieval.needs_retry
            and settings.RAG_CRAG_RETRY_ENABLED
            and query_plan.complexity != QueryComplexity.COMPLEX
        ):
            logger.info(
                "CRAG triggered query rewrite retry for low retrieval confidence."
            )
            rewritten = await rewrite_query(
                request.message, history_texts, client=self.gemini_client
            )
            retry_embedding = await self.embedder.embed_query(rewritten)
            query_plan.queries.append(rewritten)
            query_plan.embeddings.append(retry_embedding)

            retrieval = await retrieve_context(
                query_plan=query_plan,
                workspace_ids=[request.workspace_id],
                tenant_id=context.tenant_id,
                session=self.uow.session,
                reranker=self.reranker,
                original_query=rewritten,
            )

        # 7. Generation Pipeline (Streaming Synthesis)
        full_text = ""
        citations: list[dict[str, Any]] = []

        async for event in stream_synthesis(
            query=request.message,
            chunks=retrieval.chunks,
            running_summary=session.running_summary,
            client=self.gemini_client,
        ):
            yield event
            if event.type == "done":
                full_text = event.data.get("full_text", "")
            elif event.type == "citations":
                citations = event.data

        # 8. Persist User and Assistant Messages
        retrieved_chunk_ids = [str(c.id) for c in retrieval.chunks]
        await self._persist_messages(
            session=session,
            user_query=request.message,
            assistant_response=full_text,
            citations=citations,
            retrieved_chunk_ids=retrieved_chunk_ids,
            context=context,
        )

        # Auto-title on first message if needed
        if session.message_count <= 2 or session.title == "New Conversation":
            await self.session_service.auto_title(
                session.id, request.message, client=self.gemini_client
            )

        # Update running summary periodically
        if session.message_count % settings.RAG_MEMORY_WINDOW == 0:
            updated_messages = await get_recent_messages(
                session=self.uow.session,
                session_id=session.id,
                tenant_id=context.tenant_id,
                limit=settings.RAG_MEMORY_WINDOW,
            )
            await self.session_service.update_summary(
                session.id, updated_messages, client=self.gemini_client
            )

        # Write to Semantic Cache if single-turn query
        if not history_texts and settings.ENABLE_SEMANTIC_CACHE and full_text:
            if query_embedding is None:
                query_embedding = await self.embedder.embed_query(request.message)
            await self.cache.set(
                query_embedding=query_embedding,
                workspace_id=request.workspace_id,
                query_text=request.message,
                response_text=full_text,
                citations=citations,
            )

    async def _resolve_session(
        self, request: ChatRequest, context: RequestContext
    ) -> ChatSession:
        """Resolve session by ID or create a new session if not supplied."""
        if request.session_id:
            return await self.session_service.get(request.session_id)

        create_data = ChatSessionCreate(
            workspace_id=request.workspace_id,
            title="New Conversation",
        )
        return await self.session_service.create(create_data)

    async def _persist_messages(
        self,
        session: ChatSession,
        user_query: str,
        assistant_response: str,
        citations: list[dict[str, Any]],
        retrieved_chunk_ids: list[str],
        context: RequestContext,
    ) -> None:
        """Save user query and assistant response messages to the database and update session statistics."""
        user_msg = ChatMessage(
            id=uuid.uuid4(),
            tenant_id=context.tenant_id,
            session_id=session.id,
            role="user",
            content=user_query,
            token_count=len(user_query.split()),
        )

        asst_msg = ChatMessage(
            id=uuid.uuid4(),
            tenant_id=context.tenant_id,
            session_id=session.id,
            role="assistant",
            content=assistant_response,
            citations=citations,
            retrieved_chunks=retrieved_chunk_ids,
            token_count=len(assistant_response.split()),
        )

        self.uow.session.add(user_msg)
        self.uow.session.add(asst_msg)

        session.message_count += 2
        session.total_tokens += user_msg.token_count + asst_msg.token_count
        await self.uow.flush()
