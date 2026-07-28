from app.modules.documents.schemas import ScoredChunk

GROUNDED_SYSTEM_PROMPT = """You are an enterprise AI assistant for ContextHub.
Your task is to answer user questions accurately and professionally based ONLY on the provided context documents.

## Strict Rules
1. Rely EXCLUSIVELY on the provided context documents. If the context does not contain enough information to answer the question, state:
   "I cannot find the answer in the provided documents."
2. Cite your sources using inline numeric markers e.g. [^1], [^2]. Every key statement or claim must reference its specific source marker.
3. Be concise, direct, and structured in your response.
4. Never invent, extrapolate, or bring in outside information not explicitly stated in the context.
5. If the question asks for comparison or multiple parts, answer each part clearly with relevant citations.
"""


def build_grounded_prompt(
    query: str,
    chunks: list[ScoredChunk],
    running_summary: str | None = None,
    history: list[str] | None = None,
) -> tuple[str, str]:
    """Build system instructions and user prompt containing context chunks with marker numbers [^1], [^2].

    Returns:
        tuple[str, str]: (system_prompt, user_prompt)
    """
    context_blocks: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        doc_name = chunk.metadata.get("document_name", "Unknown Document")
        pages = chunk.metadata.get("page_numbers", [])
        page_str = f", Pages: {pages}" if pages else ""
        context_blocks.append(
            f"[^{idx}] Document: {doc_name}{page_str}\n{chunk.content.strip()}"
        )

    formatted_context = (
        "\n\n---\n\n".join(context_blocks)
        if context_blocks
        else "No relevant documents found."
    )

    summary_block = (
        f"## Conversation Summary\n{running_summary}\n\n" if running_summary else ""
    )

    history_block = (
        f"## Recent Conversation History\n" + "\n".join(history) + "\n\n"
        if history
        else ""
    )

    user_prompt = (
        f"{summary_block}"
        f"{history_block}"
        f"## Context Documents\n"
        f"{formatted_context}\n\n"
        f"---\n\n"
        f"## User Question\n"
        f"{query}\n\n"
        f"Answer:"
    )

    return GROUNDED_SYSTEM_PROMPT, user_prompt
