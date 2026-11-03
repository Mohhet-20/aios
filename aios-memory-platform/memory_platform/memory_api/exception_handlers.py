"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from memory_platform.core.exceptions import (
    AuthorizationError,
    ConcurrentModificationError,
    ConflictError,
    DocumentProcessingError,
    EmbeddingDimensionMismatchError,
    GraphCycleError,
    InvalidTransitionError,
    MemoryPlatformError,
    NotFoundError,
    RetentionPolicyViolationError,
    TokenBudgetExceededError,
    UnsupportedDocumentTypeError,
    ValidationError,
)

# Order matters: subclasses (e.g. UnsupportedDocumentTypeError) must be
# checked before their parent (DocumentProcessingError).
_STATUS_BY_EXCEPTION: list[tuple[type[MemoryPlatformError], int]] = [
    (NotFoundError, 404),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (RetentionPolicyViolationError, 409),
    (UnsupportedDocumentTypeError, 400),
    (DocumentProcessingError, 422),
    (EmbeddingDimensionMismatchError, 422),
    (TokenBudgetExceededError, 422),
    (GraphCycleError, 400),
    (ValidationError, 422),
]


def _status_for(exc: MemoryPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MemoryPlatformError)
    async def _handle_platform_error(request: Request, exc: MemoryPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
