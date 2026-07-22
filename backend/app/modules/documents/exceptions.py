from fastapi import status

from app.core.exceptions import ServiceError


class RetrievalError(ServiceError):
    """Raised when hybrid retrieval fails."""

    def __init__(self, detail: str = "Retrieval failed.") -> None:
        super().__init__(detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class DLPViolation(ServiceError):
    """Raised when DLP policy rejects content."""

    def __init__(self, detail: str = "Content rejected by DLP policy.") -> None:
        super().__init__(detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class EmbeddingError(ServiceError):
    """Raised when embedding generation fails."""

    def __init__(self, detail: str = "Embedding generation failed.") -> None:
        super().__init__(detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
