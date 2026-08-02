import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.core.clients import CohereClient, GeminiClient
from app.core.config import settings
from app.core.context import RequestContext
from app.core.exceptions import ServiceError
from app.core.uow import UnitOfWork
from app.modules.chat.cache.semantic_cache import SemanticCache
from app.modules.chat.generation import stream_synthesis
from app.modules.chat.grounding import check_faithfulness, compute_composite_confidence
from app.modules.chat.memory import (
    ChatSessionService,
    format_history_for_prompt,
    get_recent_messages,
)
from app.modules.chat.models import ChatMessage, ChatSession
from app.modules.chat.query import QueryComplexity, QueryPlan, prepare_queries
from app.modules.chat.query.rewriter import rewrite_query
from app.modules.chat.retrieval import Reranker, retrieve_context
from app.modules.chat.schemas import ChatRequest, ChatSessionCreate, SSEEvent
from app.modules.documents.embeddings import EmbeddingProvider
from app.modules.documents.models import Workspace
from app.utils.pricing import calculate_model_cost

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        uow: UnitOfWork,
        gemini_client: GeminiClient | None = None,
        cohere_client: CohereClient | None = None,
    ) -> None:
        self.uow = uow
        self.gemini_client = gemini_client or GeminiClient()
        self.embedder = EmbeddingProvider(client=self.gemini_client)
        self.reranker = Reranker(cohere_client=cohere_client or CohereClient())
        self.cache = SemanticCache()
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
                cached = await self.cache.get(
                    session=self.uow.session,
                    query_embedding=query_embedding,
                    workspace_id=request.workspace_id,
                )
                if cached:
                    citations = cached.get("citations", [])
                    if citations:
                        yield SSEEvent(type="citations", data=citations)
                    yield SSEEvent(type="token", data={"text": cached["content"]})
                    yield SSEEvent(
                        type="done",
                        data={
                            "full_text": cached["content"],
                            "cached": True,
                            "similarity": cached.get("similarity"),
                        },
                    )

                    prompt_tokens = len(request.message.split())
                    completion_tokens = len(cached["content"].split())
                    await self._persist_messages(
                        session=session,
                        user_query=request.message,
                        assistant_response=cached["content"],
                        citations=cached.get("citations", []),
                        context=context,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )
                    await self.uow.commit()
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
            session=self.uow.session,
            reranker=self.reranker,
            original_query=request.message,
            document_ids=request.document_ids,
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
            retry_plan = QueryPlan(
                queries=[rewritten],
                embeddings=[retry_embedding],
                complexity=query_plan.complexity,
                rewritten_query=rewritten,
            )

            retrieval = await retrieve_context(
                query_plan=retry_plan,
                workspace_ids=[request.workspace_id],
                session=self.uow.session,
                reranker=self.reranker,
                original_query=rewritten,
                document_ids=request.document_ids,
            )

        # Release DB connection during LLM synthesis
        running_summary = session.running_summary
        session_id = session.id
        await self.uow.commit()

        # 7. Stream synthesis response
        full_text = ""
        citations: list[dict[str, Any]] = []
        usage_data: dict[str, int] = {}

        async for event in stream_synthesis(
            query=request.message,
            chunks=retrieval.chunks,
            running_summary=running_summary,
            client=self.gemini_client,
            model=request.model,
            history=history_texts,
        ):
            yield event
            if event.type == "done":
                full_text = event.data.get("full_text", "")
                usage_data = event.data.get("usage", {})
            elif event.type == "citations":
                citations = event.data

        # Evaluate grounding and composite confidence
        faithfulness_score, _ = check_faithfulness(full_text, retrieval.chunks)
        citation_coverage = min(1.0, len(citations) / max(len(full_text.split(".")), 1))
        composite_confidence = compute_composite_confidence(
            retrieval_confidence=retrieval.confidence,
            faithfulness_score=faithfulness_score,
            citation_coverage=citation_coverage,
        )

        # Calculate cost via model pricing utility
        prompt_tokens = usage_data.get("prompt_tokens") or len(request.message.split())
        completion_tokens = usage_data.get("completion_tokens") or len(
            full_text.split()
        )
        cost_usd = calculate_model_cost(
            model_name=settings.RAG_CHAT_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        # 8. Save session history
        user_msg, asst_msg = await self._persist_messages(
            session=session,
            user_query=request.message,
            assistant_response=full_text,
            citations=citations,
            context=context,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            confidence_score=composite_confidence,
        )

        # Auto-title on first message if needed
        if session.message_count <= 2 or session.title == "New Conversation":
            await self.session_service.auto_title(
                session, request.message, client=self.gemini_client
            )

        # Update running summary periodically using current turn messages
        if session.message_count % settings.RAG_MEMORY_WINDOW == 0:
            await self.session_service.update_summary(
                session, [user_msg, asst_msg], client=self.gemini_client
            )

        # Write to Semantic Cache if single-turn query
        if not history_texts and settings.ENABLE_SEMANTIC_CACHE and full_text:
            if query_embedding is None:
                query_embedding = await self.embedder.embed_query(request.message)
            await self.cache.set(
                session=self.uow.session,
                query_embedding=query_embedding,
                workspace_id=request.workspace_id,
                tenant_id=context.tenant_id,
                query_text=request.message,
                response_text=full_text,
                citations=citations,
            )

        await self.uow.commit()

    async def _resolve_session(
        self, request: ChatRequest, context: RequestContext
    ) -> ChatSession:
        """Resolve session by ID or create a new session if not supplied."""
        if request.session_id:
            return await self.session_service.get(
                tenant_id=context.tenant_id,
                session_id=request.session_id,
                user_id=context.user_id,
            )

        workspace = await self.uow.session.get(Workspace, request.workspace_id)
        if (
            workspace is None
            or workspace.tenant_id != context.tenant_id
            or not workspace.is_active
        ):
            raise ServiceError("Workspace not found", status_code=404)

        return await self.session_service.create_for_workspace(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            workspace=workspace,
            title="New Conversation",
        )

    async def _persist_messages(
        self,
        session: ChatSession,
        user_query: str,
        assistant_response: str,
        citations: list[dict[str, Any]],
        context: RequestContext,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float = 0.0,
        confidence_score: float | None = None,
    ) -> tuple[ChatMessage, ChatMessage]:
        """Save user query and assistant response messages to the database and update session statistics."""
        user_msg = ChatMessage(
            id=uuid.uuid4(),
            tenant_id=context.tenant_id,
            session_id=session.id,
            role="user",
            content=user_query,
            token_count=prompt_tokens,
        )

        asst_msg = ChatMessage(
            id=uuid.uuid4(),
            tenant_id=context.tenant_id,
            session_id=session.id,
            role="assistant",
            content=assistant_response,
            citations=citations,
            token_count=completion_tokens,
            cost_usd=cost_usd,
            confidence_score=confidence_score,
        )

        self.uow.session.add_all([user_msg, asst_msg])

        session.message_count += 2
        session.total_tokens += prompt_tokens + completion_tokens
        session.total_cost_usd += cost_usd
        await self.uow.flush()
        return user_msg, asst_msg
