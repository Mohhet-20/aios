"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from analytics_platform.core.exceptions import (
    AnalyticsEngineError,
    AnalyticsPlatformError,
    AuthorizationError,
    ColumnLevelSecurityViolationError,
    ConcurrentModificationError,
    ConflictError,
    DashboardError,
    DashboardNotFoundError,
    DataLineageNotFoundError,
    EventIngestionError,
    ForecastError,
    ForecastGenerationFailedError,
    ForecastNotFoundError,
    GovernanceError,
    InsufficientHistoryError,
    InvalidTransitionError,
    KpiError,
    KpiNotFoundError,
    KpiThresholdBreachedError,
    MetricDefinitionNotFoundError,
    NotFoundError,
    ObservabilityError,
    PermissionDeniedError,
    RecommendationError,
    RecommendationNotFoundError,
    ReportError,
    ReportGenerationFailedError,
    ReportNotFoundError,
    RollupNotFoundError,
    RowLevelSecurityViolationError,
    SavedViewNotFoundError,
    TenantIsolationError,
    TooManyWidgetsError,
    UnsupportedAnalyticsDomainError,
    UnsupportedDataSourceError,
    UnsupportedForecastTypeError,
    UnsupportedKpiScopeError,
    UnsupportedRecommendationCategoryError,
    UnsupportedReportTypeError,
    UnsupportedRollupPeriodError,
    UnsupportedVisualizationTypeError,
    UsageRecordNotFoundError,
    ValidationError,
    WarehouseError,
    WidgetNotFoundError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[AnalyticsPlatformError], int]] = [
    (NotFoundError, 404),
    # data warehouse / metrics registry
    (MetricDefinitionNotFoundError, 404),
    (UnsupportedDataSourceError, 422),
    (EventIngestionError, 422),
    (WarehouseError, 400),
    # analytics / aggregation engine
    (UnsupportedAnalyticsDomainError, 422),
    (UnsupportedRollupPeriodError, 422),
    (RollupNotFoundError, 404),
    (AnalyticsEngineError, 400),
    # KPI engine
    (KpiNotFoundError, 404),
    (UnsupportedKpiScopeError, 422),
    (KpiThresholdBreachedError, 422),
    (KpiError, 400),
    # reporting platform
    (ReportNotFoundError, 404),
    (UnsupportedReportTypeError, 422),
    (ReportGenerationFailedError, 422),
    (ReportError, 400),
    # forecasting engine
    (ForecastNotFoundError, 404),
    (UnsupportedForecastTypeError, 422),
    (InsufficientHistoryError, 422),
    (ForecastGenerationFailedError, 422),
    (ForecastError, 400),
    # recommendation engine
    (RecommendationNotFoundError, 404),
    (UnsupportedRecommendationCategoryError, 422),
    (RecommendationError, 400),
    # visualization / dashboard platform
    (DashboardNotFoundError, 404),
    (WidgetNotFoundError, 404),
    (SavedViewNotFoundError, 404),
    (TooManyWidgetsError, 422),
    (UnsupportedVisualizationTypeError, 422),
    (DashboardError, 400),
    # security / governance
    (RowLevelSecurityViolationError, 403),
    (ColumnLevelSecurityViolationError, 403),
    (DataLineageNotFoundError, 404),
    (GovernanceError, 400),
    # observability
    (UsageRecordNotFoundError, 404),
    (ObservabilityError, 400),
    # base group
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: AnalyticsPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AnalyticsPlatformError)
    async def _handle_platform_error(request: Request, exc: AnalyticsPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
