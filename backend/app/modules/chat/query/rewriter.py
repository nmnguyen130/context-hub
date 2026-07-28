from app.core.clients import GeminiClient


async def rewrite_query(
    query: str,
    history: list[str],
    client: GeminiClient | None = None,
) -> str:
    """Rewrite query using conversation history to resolve pronouns."""
    client = client or GeminiClient()
    history_text = "\n".join(history[-4:]) if history else "None"
    prompt = (
        "Rewrite the user query to be self-contained and search-optimized. "
        "Resolve pronouns using conversation history. "
        "Output ONLY the rewritten query.\n\n"
        f"History:\n{history_text}\n\nQuery: {query}"
    )
    return (await client.generate(prompt, temperature=0.0)).strip()
