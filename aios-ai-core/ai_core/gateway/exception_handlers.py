"""Maps AI Core exceptions to HTTP status codes with a consistent JSON
error envelope, so every gateway endpoint fails predictably instead of
leaking a raw 500 + traceback."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ai_core.utils.exceptions import (
    AICoreError,
    AllProvidersFailedError,
    CostLimitExceededError,
    ModelNotFoundError,
    NoAvailableModelError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    RateLimitExceededError,
    RequestValidationError,
    StructuredOutputError,
    ToolPermissionDeniedError,
)

_STATUS_MAP: list[tuple[type[AICoreError], int]] = [
    (RequestValidationError, 400),
    (ProviderAuthenticationError, 401),
    (ToolPermissionDeniedError, 403),
    (ModelNotFoundError, 404),
    (ProviderRateLimitError, 429),
    (RateLimitExceededError, 429),
    (CostLimitExceededError, 402),
    (StructuredOutputError, 422),
    (NoAvailableModelError, 503),
    (AllProvidersFailedError, 503),
]


def _status_for(exc: AICoreError) -> int:
    for exc_type, status in _STATUS_MAP:
        if isinstance(exc, exc_type):
            return status
    return 500


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AICoreError)
    async def _handle_ai_core_error(request: Request, exc: AICoreError) -> JSONResponse:
        return JSONResponse(
            status_code=_status_for(exc),
            content={"error": {"type": type(exc).__name__, "message": str(exc)}},
        )
