"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service. Auth is intentionally minimal here, matching every sibling
AIOS platform: this platform expects to sit behind an already-
authenticated gateway (in practice, the Identity Platform) that
forwards the caller's tenant via `X-Tenant-Id` and, where relevant, the
acting principal via `X-User-Id`. Every service is built fresh per
request off a per-request `RepositoryRegistry`/`AsyncSession`, since a
session must never be shared across concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from observability_platform.alerts.escalation_service import AlertEscalationService
from observability_platform.alerts.evaluation_service import AlertEvaluationService
from observability_platform.alerts.maintenance_window_service import MaintenanceWindowService
from observability_platform.alerts.rule_service import AlertRuleService
from observability_platform.alerts.suppression_service import AlertSuppressionService
from observability_platform.analytics.performance_service import PerformanceAnalysisService
from observability_platform.capacity.forecast_service import CapacityForecastService
from observability_platform.config.settings import Settings, get_settings
from observability_platform.dashboards.dashboard_service import DashboardService
from observability_platform.database.session import session_scope
from observability_platform.governance.audit_service import AuditService
from observability_platform.governance.permission_service import PermissionService
from observability_platform.governance.retention_service import RetentionOrchestrationService
from observability_platform.health.aggregation_service import HealthAggregationService
from observability_platform.health.healthcheck_service import HealthCheckService
from observability_platform.incidents.incident_service import IncidentService
from observability_platform.incidents.postmortem_service import PostmortemService
from observability_platform.incidents.timeline_service import IncidentTimelineService
from observability_platform.logs.ingest_service import LogIngestService
from observability_platform.logs.retention_service import LogRetentionService
from observability_platform.logs.search_service import LogSearchService
from observability_platform.metrics.ingest_service import MetricIngestService
from observability_platform.metrics.query_service import MetricQueryService
from observability_platform.repositories.registry import RepositoryRegistry
from observability_platform.reporting.report_service import ReportService
from observability_platform.topology.dependency_service import TopologyDependencyService
from observability_platform.topology.service_map_service import ServiceMapService
from observability_platform.tracing.dependency_service import TraceDependencyService
from observability_platform.tracing.span_service import SpanService
from observability_platform.tracing.trace_service import TraceService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned (see `database/session.py`'s docstring for the contrast
    with the bare, test-oriented `get_db_session`)."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — a lot of
    what this platform ingests (logs, metrics, spans, automated alert
    evaluations) legitimately comes from a system process with no human
    actor behind it."""
    return x_user_id


# -- logging ------------------------------------------------------------------
async def get_log_ingest_service(repos: RepositoryRegistry = Depends(get_repos)) -> LogIngestService:
    return LogIngestService(repos)


async def get_log_search_service(repos: RepositoryRegistry = Depends(get_repos)) -> LogSearchService:
    return LogSearchService(repos)


async def get_log_retention_service(repos: RepositoryRegistry = Depends(get_repos)) -> LogRetentionService:
    return LogRetentionService(repos)


# -- metrics -------------------------------------------------------------------
async def get_metric_ingest_service(repos: RepositoryRegistry = Depends(get_repos)) -> MetricIngestService:
    return MetricIngestService(repos)


async def get_metric_query_service(repos: RepositoryRegistry = Depends(get_repos)) -> MetricQueryService:
    return MetricQueryService(repos)


# -- tracing -------------------------------------------------------------------
async def get_span_service(repos: RepositoryRegistry = Depends(get_repos)) -> SpanService:
    return SpanService(repos)


async def get_trace_service(repos: RepositoryRegistry = Depends(get_repos)) -> TraceService:
    return TraceService(repos)


async def get_trace_dependency_service(repos: RepositoryRegistry = Depends(get_repos)) -> TraceDependencyService:
    return TraceDependencyService(repos)


# -- health ----------------------------------------------------------------------
async def get_healthcheck_service(repos: RepositoryRegistry = Depends(get_repos)) -> HealthCheckService:
    return HealthCheckService(repos)


async def get_health_aggregation_service(repos: RepositoryRegistry = Depends(get_repos)) -> HealthAggregationService:
    return HealthAggregationService(repos)


# -- alerts -----------------------------------------------------------------------
async def get_alert_rule_service(repos: RepositoryRegistry = Depends(get_repos)) -> AlertRuleService:
    return AlertRuleService(repos)


async def get_alert_evaluation_service(repos: RepositoryRegistry = Depends(get_repos)) -> AlertEvaluationService:
    return AlertEvaluationService(repos)


async def get_alert_suppression_service(repos: RepositoryRegistry = Depends(get_repos)) -> AlertSuppressionService:
    return AlertSuppressionService(repos)


async def get_alert_escalation_service(repos: RepositoryRegistry = Depends(get_repos)) -> AlertEscalationService:
    return AlertEscalationService(repos)


async def get_maintenance_window_service(repos: RepositoryRegistry = Depends(get_repos)) -> MaintenanceWindowService:
    return MaintenanceWindowService(repos)


# -- incidents --------------------------------------------------------------------
async def get_incident_service(repos: RepositoryRegistry = Depends(get_repos)) -> IncidentService:
    return IncidentService(repos)


async def get_incident_timeline_service(repos: RepositoryRegistry = Depends(get_repos)) -> IncidentTimelineService:
    return IncidentTimelineService(repos)


async def get_postmortem_service(repos: RepositoryRegistry = Depends(get_repos)) -> PostmortemService:
    return PostmortemService(repos)


# -- performance / capacity ---------------------------------------------------------
async def get_performance_analysis_service(repos: RepositoryRegistry = Depends(get_repos)) -> PerformanceAnalysisService:
    return PerformanceAnalysisService(repos)


async def get_capacity_forecast_service(repos: RepositoryRegistry = Depends(get_repos)) -> CapacityForecastService:
    return CapacityForecastService(repos)


# -- topology --------------------------------------------------------------------------
async def get_service_map_service(repos: RepositoryRegistry = Depends(get_repos)) -> ServiceMapService:
    return ServiceMapService(repos)


async def get_topology_dependency_service(repos: RepositoryRegistry = Depends(get_repos)) -> TopologyDependencyService:
    return TopologyDependencyService(repos)


# -- dashboards / reporting --------------------------------------------------------------
async def get_dashboard_service(repos: RepositoryRegistry = Depends(get_repos)) -> DashboardService:
    return DashboardService(repos)


async def get_report_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReportService:
    return ReportService(repos)


# -- governance ---------------------------------------------------------------------------
async def get_permission_service(repos: RepositoryRegistry = Depends(get_repos)) -> PermissionService:
    return PermissionService(repos)


async def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


async def get_retention_orchestration_service(repos: RepositoryRegistry = Depends(get_repos)) -> RetentionOrchestrationService:
    return RetentionOrchestrationService(repos)
