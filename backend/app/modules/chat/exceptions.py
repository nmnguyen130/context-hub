from fastapi import status

from app.core.exceptions import ServiceError


class ChatSessionNotFoundError(ServiceError):
    """Raised when a chat session cannot be found."""

    def __init__(self, detail: str = "Chat session not found.") -> None:
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)
