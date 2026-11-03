"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from workflow_platform.core.exceptions import (
    ApprovalDeniedError,
    ApprovalRequiredError,
    AuthorizationError,
    CheckpointError,
    CompensationError,
    ConcurrencyLimitExceededError,
    ConcurrentModificationError,
    ConflictError,
    InvalidTransitionError,
    NodeExecutionError,
    NodeTimeoutError,
    NotFoundError,
    RateLimitExceededError,
    RecursionLimitExceededError,
    RetryExhaustedError,
    ScheduleError,
    UnknownNodeTypeError,
    ValidationError,
    VariableResolutionError,
    WebhookDeliveryError,
    WorkflowCycleError,
    WorkflowPlatformError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[WorkflowPlatformError], int]] = [
    (NotFoundError, 404),
    (AuthorizationError, 403),
    (ApprovalRequiredError, 403),
    (ApprovalDeniedError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (WorkflowCycleError, 400),
    (RecursionLimitExceededError, 400),
    (UnknownNodeTypeError, 400),
    (ConcurrencyLimitExceededError, 429),
    (RateLimitExceededError, 429),
    (NodeTimeoutError, 408),
    (RetryExhaustedError, 422),
    (CompensationError, 500),
    (CheckpointError, 500),
    (WebhookDeliveryError, 502),
    (ScheduleError, 422),
    (NodeExecutionError, 422),
    (VariableResolutionError, 422),
    (ValidationError, 422),
]


def _status_for(exc: WorkflowPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(WorkflowPlatformError)
    async def _handle_platform_error(request: Request, exc: WorkflowPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
