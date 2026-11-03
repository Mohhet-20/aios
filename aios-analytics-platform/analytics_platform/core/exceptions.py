"""Exception hierarchy for the Enterprise Analytics, Business
Intelligence & Executive Reporting Platform."""
from __future__ import annotations


class AnalyticsPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(AnalyticsPlatformError):
    pass


class ValidationError(AnalyticsPlatformError):
    pass


class ConflictError(AnalyticsPlatformError):
    pass


class ConcurrentModificationError(AnalyticsPlatformError):
    pass


class AuthorizationError(AnalyticsPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(AnalyticsPlatformError):
    """Raised on an illegal lifecycle transition (report, forecast job,
    recommendation, dashboard, KPI, data export job)."""


# -- data warehouse / metrics registry -------------------------------------------------------------

class WarehouseError(AnalyticsPlatformError):
    pass


class MetricDefinitionNotFoundError(WarehouseError):
    pass


class UnsupportedDataSourceError(WarehouseError):
    pass


class EventIngestionError(WarehouseError):
    pass


# -- analytics / aggregation engine -----------------------------------------------------------------

class AnalyticsEngineError(AnalyticsPlatformError):
    pass


class UnsupportedAnalyticsDomainError(AnalyticsEngineError):
    pass


class UnsupportedRollupPeriodError(AnalyticsEngineError):
    pass


class RollupNotFoundError(AnalyticsEngineError):
    pass


# -- KPI engine ---------------------------------------------------------------------------------------

class KpiError(AnalyticsPlatformError):
    pass


class KpiNotFoundError(KpiError):
    pass


class UnsupportedKpiScopeError(KpiError):
    pass


class KpiThresholdBreachedError(KpiError):
    pass


# -- reporting platform ---------------------------------------------------------------------------------

class ReportError(AnalyticsPlatformError):
    pass


class ReportNotFoundError(ReportError):
    pass


class UnsupportedReportTypeError(ReportError):
    pass


class ReportGenerationFailedError(ReportError):
    pass


# -- forecasting engine ---------------------------------------------------------------------------------

class ForecastError(AnalyticsPlatformError):
    pass


class ForecastNotFoundError(ForecastError):
    pass


class UnsupportedForecastTypeError(ForecastError):
    pass


class InsufficientHistoryError(ForecastError):
    pass


class ForecastGenerationFailedError(ForecastError):
    pass


# -- recommendation engine ---------------------------------------------------------------------------------

class RecommendationError(AnalyticsPlatformError):
    pass


class RecommendationNotFoundError(RecommendationError):
    pass


class UnsupportedRecommendationCategoryError(RecommendationError):
    pass


# -- visualization / dashboard platform ---------------------------------------------------------------------

class DashboardError(AnalyticsPlatformError):
    pass


class DashboardNotFoundError(DashboardError):
    pass


class WidgetNotFoundError(DashboardError):
    pass


class SavedViewNotFoundError(DashboardError):
    pass


class TooManyWidgetsError(DashboardError):
    pass


class UnsupportedVisualizationTypeError(DashboardError):
    pass


# -- security / governance ---------------------------------------------------------------------------------

class GovernanceError(AnalyticsPlatformError):
    pass


class RowLevelSecurityViolationError(GovernanceError):
    pass


class ColumnLevelSecurityViolationError(GovernanceError):
    pass


class DataLineageNotFoundError(GovernanceError):
    pass


# -- observability ---------------------------------------------------------------------------------------

class ObservabilityError(AnalyticsPlatformError):
    pass


class UsageRecordNotFoundError(ObservabilityError):
    pass
