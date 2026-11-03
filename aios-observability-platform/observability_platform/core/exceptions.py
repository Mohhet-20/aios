"""Exception hierarchy for the Enterprise Monitoring, Logging &
Observability Platform."""
from __future__ import annotations


class ObservabilityPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(ObservabilityPlatformError):
    pass


class ValidationError(ObservabilityPlatformError):
    pass


class ConflictError(ObservabilityPlatformError):
    pass


class ConcurrentModificationError(ObservabilityPlatformError):
    pass


class AuthorizationError(ObservabilityPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    """Raised when a caller attempts to read/write a row belonging to a
    different tenant than the one on their request context."""


class InvalidTransitionError(ObservabilityPlatformError):
    """Raised on an illegal lifecycle transition (alert, incident,
    health check, maintenance window, etc.)."""


# -- logging -----------------------------------------------------------------

class LogIngestError(ObservabilityPlatformError):
    pass


class LogPayloadTooLargeError(LogIngestError):
    pass


class LogSearchError(ObservabilityPlatformError):
    pass


# -- metrics -------------------------------------------------------------------

class MetricIngestError(ObservabilityPlatformError):
    pass


class MetricBatchTooLargeError(MetricIngestError):
    pass


class MetricQueryError(ObservabilityPlatformError):
    pass


class HighCardinalityError(MetricIngestError):
    pass


# -- tracing ---------------------------------------------------------------------

class TraceError(ObservabilityPlatformError):
    pass


class SpanError(ObservabilityPlatformError):
    pass


class TraceTooLargeError(TraceError):
    pass


class OrphanSpanError(SpanError):
    """A span referencing a parent_span_id that doesn't exist in the trace."""


# -- health ------------------------------------------------------------------------

class HealthCheckError(ObservabilityPlatformError):
    pass


class ComponentNotRegisteredError(HealthCheckError):
    pass


# -- alerts -----------------------------------------------------------------------

class AlertError(ObservabilityPlatformError):
    pass


class AlertRuleError(AlertError):
    pass


class AlertAlreadyResolvedError(AlertError):
    pass


class MaintenanceWindowError(ObservabilityPlatformError):
    pass


# -- incidents --------------------------------------------------------------------

class IncidentError(ObservabilityPlatformError):
    pass


class IncidentAlreadyClosedError(IncidentError):
    pass


class EscalationPolicyError(ObservabilityPlatformError):
    pass


# -- capacity / analytics ----------------------------------------------------------

class CapacityForecastError(ObservabilityPlatformError):
    pass


class InsufficientHistoryError(CapacityForecastError):
    pass


class PerformanceAnalysisError(ObservabilityPlatformError):
    pass


# -- topology -----------------------------------------------------------------------

class TopologyError(ObservabilityPlatformError):
    pass


class DependencyCycleError(TopologyError):
    pass


# -- dashboards / reporting --------------------------------------------------------

class DashboardError(ObservabilityPlatformError):
    pass


class ReportError(ObservabilityPlatformError):
    pass


class ReportGenerationError(ReportError):
    pass


# -- governance -----------------------------------------------------------------------

class GovernanceError(ObservabilityPlatformError):
    pass


class RetentionPolicyError(GovernanceError):
    pass


class AuditLogError(GovernanceError):
    pass
