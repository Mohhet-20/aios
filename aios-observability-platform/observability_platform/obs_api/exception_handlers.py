"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from observability_platform.core.exceptions import (
    AlertAlreadyResolvedError,
    AlertError,
    AlertRuleError,
    AuditLogError,
    AuthorizationError,
    CapacityForecastError,
    ComponentNotRegisteredError,
    ConcurrentModificationError,
    ConflictError,
    DashboardError,
    DependencyCycleError,
    EscalationPolicyError,
    GovernanceError,
    HealthCheckError,
    HighCardinalityError,
    IncidentAlreadyClosedError,
    IncidentError,
    InsufficientHistoryError,
    InvalidTransitionError,
    LogIngestError,
    LogPayloadTooLargeError,
    LogSearchError,
    MaintenanceWindowError,
    MetricBatchTooLargeError,
    MetricIngestError,
    MetricQueryError,
    NotFoundError,
    ObservabilityPlatformError,
    OrphanSpanError,
    PerformanceAnalysisError,
    PermissionDeniedError,
    ReportError,
    ReportGenerationError,
    RetentionPolicyError,
    SpanError,
    TenantIsolationError,
    TopologyError,
    TraceError,
    TraceTooLargeError,
    ValidationError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[ObservabilityPlatformError], int]] = [
    (NotFoundError, 404),
    (ComponentNotRegisteredError, 404),
    (LogPayloadTooLargeError, 413),
    (LogIngestError, 400),
    (LogSearchError, 400),
    (MetricBatchTooLargeError, 413),
    (HighCardinalityError, 422),
    (MetricIngestError, 400),
    (MetricQueryError, 400),
    (TraceTooLargeError, 413),
    (OrphanSpanError, 422),
    (SpanError, 400),
    (TraceError, 400),
    (HealthCheckError, 400),
    (AlertAlreadyResolvedError, 409),
    (AlertRuleError, 400),
    (AlertError, 400),
    (MaintenanceWindowError, 400),
    (IncidentAlreadyClosedError, 409),
    (IncidentError, 400),
    (EscalationPolicyError, 400),
    (InsufficientHistoryError, 422),
    (CapacityForecastError, 400),
    (PerformanceAnalysisError, 400),
    (DependencyCycleError, 422),
    (TopologyError, 400),
    (DashboardError, 400),
    (ReportGenerationError, 500),
    (ReportError, 400),
    (RetentionPolicyError, 400),
    (AuditLogError, 400),
    (GovernanceError, 400),
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: ObservabilityPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ObservabilityPlatformError)
    async def _handle_platform_error(request: Request, exc: ObservabilityPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
