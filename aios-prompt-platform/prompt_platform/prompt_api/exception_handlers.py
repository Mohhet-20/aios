"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need
try/except blocks either."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from prompt_platform.core.exceptions import (
    ApprovalRequiredError,
    AuthorizationError,
    ConcurrentModificationError,
    ConflictError,
    DependencyCycleError,
    DeploymentError,
    EvalGateNotMetError,
    InvalidTransitionError,
    NotFoundError,
    PromptPlatformError,
    SecurityViolationError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[PromptPlatformError], int]] = [
    (NotFoundError, 404),
    (AuthorizationError, 403),
    (ApprovalRequiredError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (DeploymentError, 409),
    (DependencyCycleError, 400),
    (SecurityViolationError, 400),
    (EvalGateNotMetError, 422),
    (ValidationError, 422),
]


def _status_for(exc: PromptPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PromptPlatformError)
    async def _handle_platform_error(request: Request, exc: PromptPlatformError) -> JSONResponse:
        body: dict = {"error": exc.__class__.__name__, "detail": str(exc)}
        if isinstance(exc, EvalGateNotMetError):
            body["required"] = exc.required
            body["actual"] = exc.actual
        return JSONResponse(status_code=_status_for(exc), content=body)
