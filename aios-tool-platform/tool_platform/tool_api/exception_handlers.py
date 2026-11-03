"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tool_platform.core.exceptions import (
    ApprovalRequiredError,
    AuthorizationError,
    CheckpointError,
    ConcurrencyLimitExceededError,
    ConcurrentModificationError,
    ConflictError,
    CredentialError,
    CredentialExpiredError,
    CredentialNotFoundError,
    InvalidTransitionError,
    NetworkPolicyViolationError,
    NotFoundError,
    PluginDependencyError,
    PluginError,
    PluginIsolationError,
    PluginSignatureError,
    RateLimitExceededError,
    ResourceLimitExceededError,
    RetryExhaustedError,
    SandboxViolationError,
    SchemaValidationError,
    ToolExecutionError,
    ToolPlanningError,
    ToolPlatformError,
    ToolTimeoutError,
    UnknownToolTypeError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[ToolPlatformError], int]] = [
    (CredentialNotFoundError, 404),
    (NotFoundError, 404),
    (AuthorizationError, 403),
    (ApprovalRequiredError, 403),
    (PluginIsolationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ConcurrencyLimitExceededError, 429),
    (RateLimitExceededError, 429),
    (ToolTimeoutError, 408),
    (RetryExhaustedError, 422),
    (CheckpointError, 500),
    (SandboxViolationError, 422),
    (NetworkPolicyViolationError, 422),
    (ResourceLimitExceededError, 422),
    (CredentialExpiredError, 422),
    (CredentialError, 422),
    (PluginSignatureError, 422),
    (PluginDependencyError, 422),
    (PluginError, 422),
    (UnknownToolTypeError, 400),
    (ToolPlanningError, 422),
    (SchemaValidationError, 422),
    (ToolExecutionError, 422),
    (ValidationError, 422),
]


def _status_for(exc: ToolPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ToolPlatformError)
    async def _handle_platform_error(request: Request, exc: ToolPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
