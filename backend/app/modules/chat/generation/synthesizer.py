from collections.abc import AsyncIterator

from app.core.clients import GeminiClient
from app.modules.chat.generation.citations import extract_citations
from app.modules.chat.generation.prompts import build_grounded_prompt
from app.modules.chat.schemas import SSEEvent
from app.modules.documents.schemas import ScoredChunk


async def stream_synthesis(
    query: str,
    chunks: list[ScoredChunk],
    running_summary: str | None = None,
    client: GeminiClient | None = None,
) -> AsyncIterator[SSEEvent]:
    """Orchestrate grounded synthesis and stream SSE events (sources -> tokens -> citations -> done)."""
    client = client or GeminiClient()

    # 1. Emit sources event first
    sources_data = [
        {
            "index": idx,
            "document_id": str(c.document_id),
            "document_name": c.metadata.get("document_name", "Unknown"),
            "chunk_id": str(c.id),
            "page_numbers": c.metadata.get("page_numbers", []),
        }
        for idx, c in enumerate(chunks, start=1)
    ]
    yield SSEEvent(type="sources", data=sources_data)

    # 2. Build prompt
    system_prompt, user_prompt = build_grounded_prompt(query, chunks, running_summary)

    # 3. Stream tokens
    full_text_chunks: list[str] = []
    try:
        async for token in client.stream_generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.2,
        ):
            full_text_chunks.append(token)
            yield SSEEvent(type="token", data={"text": token})
    except Exception as exc:
        yield SSEEvent(type="error", data={"message": str(exc)})
        return

    full_text = "".join(full_text_chunks)

    # 4. Extract citations
    citations = extract_citations(full_text, chunks)
    citations_data = [c.model_dump(mode="json") for c in citations]
    yield SSEEvent(type="citations", data=citations_data)

    # 5. Emit done event
    yield SSEEvent(
        type="done",
        data={
            "full_text": full_text,
            "citation_count": len(citations),
        },
    )
