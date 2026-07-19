import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Base exception for all service and business logic errors."""

    def __init__(
        self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


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


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers for the FastAPI application."""

    @app.exception_handler(ServiceError)
    async def handle_service_error(_, exc: ServiceError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_, exc: RequestValidationError):
        errors = [
            {
                "loc": error["loc"],
                "msg": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        logger.warning("Validation error: %s", errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": errors,
            },
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(_, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_, exc: Exception):
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
