"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent_platform.core.exceptions import (
    AgentPlatformError,
    ApprovalRequiredError,
    AuthorizationError,
    ConcurrentModificationError,
    ConflictError,
    DependencyCycleError,
    ExecutionCancelledError,
    InvalidTransitionError,
    NotFoundError,
    OrchestrationError,
    RecursionLimitExceededError,
    ResourceQuotaExceededError,
    ToolPermissionError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[AgentPlatformError], int]] = [
    (NotFoundError, 404),
    (AuthorizationError, 403),
    (ApprovalRequiredError, 403),
    (ToolPermissionError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ExecutionCancelledError, 409),
    (DependencyCycleError, 400),
    (RecursionLimitExceededError, 400),
    (ResourceQuotaExceededError, 429),
    (OrchestrationError, 422),
    (ValidationError, 422),
]


def _status_for(exc: AgentPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AgentPlatformError)
    async def _handle_platform_error(request: Request, exc: AgentPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
