from fastapi import status

from app.core.exceptions import ServiceError


class ChatSessionNotFoundError(ServiceError):
    """Raised when a chat session cannot be found."""

    def __init__(self, detail: str = "Chat session not found.") -> None:
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)


class ChatGenerationError(ServiceError):
    """Raised when LLM text synthesis fails."""

    def __init__(self, detail: str = "Chat generation failed.") -> None:
        super().__init__(detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class RetrievalInsufficientError(ServiceError):
    """Raised when retrieval yields no relevant context."""

    def __init__(self, detail: str = "No relevant context found in workspace.") -> None:
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)


class SemanticCacheError(ServiceError):
    """Raised when semantic cache operations fail."""

    def __init__(self, detail: str = "Semantic cache error.") -> None:
        super().__init__(detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
