from collections.abc import AsyncIterator

from app.core.clients import GeminiClient, UsageInfo
from app.modules.chat.generation.citations import extract_citations
from app.modules.chat.generation.prompts import build_grounded_prompt
from app.modules.chat.schemas import SSEEvent
from app.modules.documents.schemas import ScoredChunk

MAX_TOKENS_SAFETY_LIMIT = 10_000


async def stream_synthesis(
    query: str,
    chunks: list[ScoredChunk],
    running_summary: str | None = None,
    client: GeminiClient | None = None,
    model: str | None = None,
    history: list[str] | None = None,
) -> AsyncIterator[SSEEvent]:
    """Stream grounded RAG LLM text synthesis with inline citations via SSE."""
    client = client or GeminiClient()

    # 1. Build structured prompt
    system_prompt, user_prompt = build_grounded_prompt(
        query, chunks, running_summary, history=history
    )

    # 2. Emit sources event first
    sources_data = [
        {
            "id": str(c.id),
            "document_id": str(c.document_id),
            "content": c.content,
            "metadata": c.metadata,
        }
        for c in chunks
    ]
    yield SSEEvent(type="sources", data=sources_data)

    # 3. Stream model response text tokens
    full_text_chunks: list[str] = []
    usage_info = UsageInfo()
    try:
        async for token in client.stream_generate(
            prompt=user_prompt,
            system=system_prompt,
            model=model,
            temperature=0.2,
            usage_info=usage_info,
        ):
            full_text_chunks.append(token)
            yield SSEEvent(type="token", data={"text": token})
            if len(full_text_chunks) >= MAX_TOKENS_SAFETY_LIMIT:
                break
    except Exception:
        yield SSEEvent(type="error", data={"message": "Assistant generation failed."})
        return

    full_text = "".join(full_text_chunks)

    # 4. Extract citations
    citations = extract_citations(full_text, chunks)
    citations_data = [c.model_dump(mode="json") for c in citations]
    yield SSEEvent(type="citations", data=citations_data)

    # 5. Emit done event
    completion_count = usage_info.completion_tokens or len(full_text_chunks)
    total_count = usage_info.total_tokens or (
        usage_info.prompt_tokens + completion_count
    )
    yield SSEEvent(
        type="done",
        data={
            "full_text": full_text,
            "citation_count": len(citations),
            "usage": {
                "prompt_tokens": usage_info.prompt_tokens,
                "completion_tokens": completion_count,
                "total_tokens": total_count,
            },
        },
    )
