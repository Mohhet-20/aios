"""FastAPI dependency wiring: DB session -> RepositoryRegistry ->
every service. Auth is intentionally minimal here, matching every
sibling AIOS platform: this platform expects to sit behind an
already-authenticated gateway (in practice, the Identity Platform)
that forwards the caller's tenant via `X-Tenant-Id` and, where
relevant, the acting principal via `X-User-Id`. Every service is
built fresh per request off a per-request `RepositoryRegistry`/
`AsyncSession`, since a session must never be shared across
concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_platform.analytics.ai_analytics_service import AiAnalyticsService
from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.analytics.business_analytics_service import BusinessAnalyticsService
from analytics_platform.analytics.financial_analytics_service import FinancialAnalyticsService
from analytics_platform.analytics.performance_analytics_service import PerformanceAnalyticsService
from analytics_platform.config.settings import Settings, get_settings
from analytics_platform.dashboards.dashboard_service import DashboardService
from analytics_platform.dashboards.saved_view_service import SavedViewService
from analytics_platform.database.session import session_scope
from analytics_platform.forecasting.forecast_job_service import ForecastJobService
from analytics_platform.kpis.kpi_service import KpiService
from analytics_platform.kpis.snapshot_service import KpiSnapshotService
from analytics_platform.observability.forecast_accuracy_service import ForecastAccuracyService
from analytics_platform.observability.query_performance_service import QueryPerformanceService
from analytics_platform.observability.recommendation_analytics_service import RecommendationAnalyticsService
from analytics_platform.observability.usage_service import UsageEventService
from analytics_platform.recommendations.recommendation_service import RecommendationService
from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.reports.report_definition_service import ReportDefinitionService
from analytics_platform.reports.report_run_service import ReportRunService
from analytics_platform.security.audit_service import AuditLogService
from analytics_platform.security.column_level_security_service import ColumnLevelSecurityService
from analytics_platform.security.lineage_service import DataLineageService
from analytics_platform.security.rbac_service import AnalyticsRbacService
from analytics_platform.security.row_level_security_service import RowLevelSecurityService
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session, scope="function")) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some of
    what this platform tracks (retention sweeps, scheduled reports,
    automated forecast runs) legitimately comes from a process with no
    human actor behind it."""
    return x_user_id


# -- data warehouse / metrics registry --------------------------------------------------------------
async def get_metric_registry_service(repos: RepositoryRegistry = Depends(get_repos)) -> MetricRegistryService:
    return MetricRegistryService(repos)


async def get_event_ingestion_service(repos: RepositoryRegistry = Depends(get_repos)) -> EventIngestionService:
    return EventIngestionService(repos, registry=MetricRegistryService(repos))


# -- analytics / aggregation engine ------------------------------------------------------------------
async def get_aggregation_engine(repos: RepositoryRegistry = Depends(get_repos)) -> AggregationEngine:
    return AggregationEngine(repos)


async def get_business_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> BusinessAnalyticsService:
    return BusinessAnalyticsService(repos)


async def get_ai_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> AiAnalyticsService:
    return AiAnalyticsService(repos)


async def get_financial_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> FinancialAnalyticsService:
    return FinancialAnalyticsService(repos)


async def get_performance_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> PerformanceAnalyticsService:
    return PerformanceAnalyticsService(repos)


# -- KPI engine ---------------------------------------------------------------------------------------
async def get_kpi_service(repos: RepositoryRegistry = Depends(get_repos)) -> KpiService:
    return KpiService(repos)


async def get_kpi_snapshot_service(repos: RepositoryRegistry = Depends(get_repos)) -> KpiSnapshotService:
    return KpiSnapshotService(repos)


# -- reporting platform ---------------------------------------------------------------------------------
async def get_report_definition_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReportDefinitionService:
    return ReportDefinitionService(repos)


async def get_report_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReportRunService:
    return ReportRunService(repos)


# -- forecasting engine ---------------------------------------------------------------------------------
async def get_forecast_job_service(repos: RepositoryRegistry = Depends(get_repos)) -> ForecastJobService:
    return ForecastJobService(repos)


# -- recommendation engine ---------------------------------------------------------------------------------
async def get_recommendation_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecommendationService:
    return RecommendationService(repos)


# -- visualization / dashboard platform ---------------------------------------------------------------------
async def get_dashboard_service(repos: RepositoryRegistry = Depends(get_repos)) -> DashboardService:
    return DashboardService(repos)


async def get_saved_view_service(repos: RepositoryRegistry = Depends(get_repos)) -> SavedViewService:
    return SavedViewService(repos)


# -- security / governance ---------------------------------------------------------------------------------
async def get_rbac_service(repos: RepositoryRegistry = Depends(get_repos)) -> AnalyticsRbacService:
    return AnalyticsRbacService(repos)


async def get_row_level_security_service(repos: RepositoryRegistry = Depends(get_repos)) -> RowLevelSecurityService:
    return RowLevelSecurityService(repos)


async def get_column_level_security_service(repos: RepositoryRegistry = Depends(get_repos)) -> ColumnLevelSecurityService:
    return ColumnLevelSecurityService(repos)


async def get_audit_log_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditLogService:
    return AuditLogService(repos)


async def get_data_lineage_service(repos: RepositoryRegistry = Depends(get_repos)) -> DataLineageService:
    return DataLineageService(repos)


# -- observability ---------------------------------------------------------------------------------------
async def get_usage_event_service(repos: RepositoryRegistry = Depends(get_repos)) -> UsageEventService:
    return UsageEventService(repos)


async def get_query_performance_service(repos: RepositoryRegistry = Depends(get_repos)) -> QueryPerformanceService:
    return QueryPerformanceService(repos)


async def get_forecast_accuracy_service(repos: RepositoryRegistry = Depends(get_repos)) -> ForecastAccuracyService:
    return ForecastAccuracyService(repos)


async def get_recommendation_analytics_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecommendationAnalyticsService:
    return RecommendationAnalyticsService(repos)
