import re

STOPWORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on",
    "at", "to", "for", "of", "with", "it", "this", "that", "from", "by", "as"
}


def tokenize(text: str) -> set[str]:
    """Tokenize text into lowercased alphanumeric words excluding standard stopwords."""
    if not text:
        return set()
    words = re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())
    return {w for w in words if w not in STOPWORDS}
