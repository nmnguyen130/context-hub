import json
import logging

from app.core.clients import GeminiClient

logger = logging.getLogger(__name__)


async def expand_query(
    query: str,
    client: GeminiClient | None = None,
    count: int = 3,
) -> list[str]:
    """Generate alternative phrasings of query for expanded retrieval."""
    client = client or GeminiClient()
    prompt = (
        f"Generate {count} alternative phrasings of this search query. "
        "Return a JSON array of strings only.\n\n"
        f"Query: {query}"
    )
    raw = await client.generate(prompt, temperature=0.3)
    try:
        parsed = json.loads(raw.strip())
        if isinstance(parsed, list):
            return [str(q) for q in parsed[:count]]
    except json.JSONDecodeError as exc:
        logger.warning("Query expansion JSON decoding failed: %s", exc)
    return [query]
