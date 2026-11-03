"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from eval_platform.core.exceptions import (
    AlertRuleError,
    ApprovalRequiredError,
    AuthorizationError,
    BenchmarkError,
    ConcurrencyLimitExceededError,
    ConcurrentModificationError,
    ConflictError,
    DatasetError,
    EvalPlatformError,
    EvaluationExecutionError,
    EvaluationTimeoutError,
    HallucinationCheckError,
    InvalidTransitionError,
    MetricComputationError,
    NotFoundError,
    RateLimitExceededError,
    RecommendationError,
    RetryExhaustedError,
    SchemaValidationError,
    UnknownEvaluationTypeError,
    UnknownMetricError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[EvalPlatformError], int]] = [
    (NotFoundError, 404),
    (AuthorizationError, 403),
    (ApprovalRequiredError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ConcurrencyLimitExceededError, 429),
    (RateLimitExceededError, 429),
    (EvaluationTimeoutError, 408),
    (RetryExhaustedError, 422),
    (UnknownMetricError, 400),
    (UnknownEvaluationTypeError, 400),
    (SchemaValidationError, 422),
    (MetricComputationError, 422),
    (EvaluationExecutionError, 422),
    (DatasetError, 422),
    (BenchmarkError, 422),
    (HallucinationCheckError, 422),
    (AlertRuleError, 422),
    (RecommendationError, 422),
    (ValidationError, 422),
]


def _status_for(exc: EvalPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EvalPlatformError)
    async def _handle_platform_error(request: Request, exc: EvalPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
