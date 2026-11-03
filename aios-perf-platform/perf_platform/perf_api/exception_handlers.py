"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from perf_platform.core.exceptions import (
    AuthorizationError,
    BenchmarkNotFoundError,
    BudgetExceededError,
    BudgetNotFoundError,
    CacheEntryNotFoundError,
    CacheError,
    ConcurrentModificationError,
    ConflictError,
    CostError,
    GpuPoolNotFoundError,
    InvalidTransitionError,
    MetricSampleInvalidError,
    NoEligibleModelTierError,
    NotFoundError,
    ObservabilityError,
    OptimizationError,
    PerfPlatformError,
    PermissionDeniedError,
    RecommendationNotFoundError,
    RoutingError,
    RoutingPolicyNotFoundError,
    ScalabilityError,
    TenantIsolationError,
    UnsupportedCacheLayerError,
    UnsupportedCostCategoryError,
    UnsupportedCostEntityTypeError,
    UnsupportedGpuPoolTypeError,
    UnsupportedModelTierError,
    UnsupportedRecommendationCategoryError,
    UnsupportedTaskComplexityError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[PerfPlatformError], int]] = [
    (NotFoundError, 404),
    # cache platform
    (CacheEntryNotFoundError, 404),
    (UnsupportedCacheLayerError, 422),
    (CacheError, 400),
    # model routing / LLM cost intelligence
    (RoutingPolicyNotFoundError, 404),
    (NoEligibleModelTierError, 422),
    (UnsupportedModelTierError, 422),
    (UnsupportedTaskComplexityError, 422),
    (RoutingError, 400),
    # cost intelligence engine
    (BudgetNotFoundError, 404),
    (BudgetExceededError, 402),
    (UnsupportedCostCategoryError, 422),
    (UnsupportedCostEntityTypeError, 422),
    (CostError, 400),
    # auto-optimization engine
    (RecommendationNotFoundError, 404),
    (UnsupportedRecommendationCategoryError, 422),
    (OptimizationError, 400),
    # observability & benchmarking
    (BenchmarkNotFoundError, 404),
    (MetricSampleInvalidError, 422),
    (ObservabilityError, 400),
    # scalability & GPU efficiency
    (GpuPoolNotFoundError, 404),
    (UnsupportedGpuPoolTypeError, 422),
    (ScalabilityError, 400),
    # common group
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: PerfPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PerfPlatformError)
    async def _handle_platform_error(request: Request, exc: PerfPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
