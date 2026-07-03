import unicodedata


def normalize_text(text: str) -> str:
    """NFC normalize for consistent Vietnamese/Unicode processing."""
    return unicodedata.normalize("NFC", text)
