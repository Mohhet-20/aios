"""Unit-of-work: lazily builds and memoizes one repository per model,
all sharing a single `AsyncSession` (and therefore the same
transaction) for the lifetime of a request or test."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from analytics_platform.repositories.analytics_repository import MetricRollupRepository
from analytics_platform.repositories.dashboards_repository import (
    DashboardRepository,
    DashboardWidgetRepository,
    SavedViewRepository,
)
from analytics_platform.repositories.exports_repository import DataExportJobRepository
from analytics_platform.repositories.forecasts_repository import ForecastJobRepository
from analytics_platform.repositories.kpis_repository import KpiDefinitionRepository, KpiSnapshotRepository
from analytics_platform.repositories.observability_repository import (
    ForecastAccuracyRepository,
    QueryPerformanceRepository,
    RecommendationOutcomeRepository,
    UsageEventRepository,
)
from analytics_platform.repositories.recommendations_repository import RecommendationRepository
from analytics_platform.repositories.reports_repository import ReportDefinitionRepository, ReportRunRepository
from analytics_platform.repositories.security_repository import (
    AnalyticsRoleGrantRepository,
    AuditLogEntryRepository,
    ColumnLevelSecurityRuleRepository,
    DataLineageEdgeRepository,
    RowLevelSecurityRuleRepository,
)
from analytics_platform.repositories.warehouse_repository import MetricDefinitionRepository, MetricEventRepository


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repos: dict[str, object] = {}

    def _get(self, key: str, cls: type) -> object:
        if key not in self._repos:
            self._repos[key] = cls(self.session)
        return self._repos[key]

    # -- data warehouse / metrics registry --
    @property
    def metric_definitions(self) -> MetricDefinitionRepository:
        return self._get("metric_definitions", MetricDefinitionRepository)

    @property
    def metric_events(self) -> MetricEventRepository:
        return self._get("metric_events", MetricEventRepository)

    # -- analytics / aggregation engine --
    @property
    def metric_rollups(self) -> MetricRollupRepository:
        return self._get("metric_rollups", MetricRollupRepository)

    # -- KPI engine --
    @property
    def kpi_definitions(self) -> KpiDefinitionRepository:
        return self._get("kpi_definitions", KpiDefinitionRepository)

    @property
    def kpi_snapshots(self) -> KpiSnapshotRepository:
        return self._get("kpi_snapshots", KpiSnapshotRepository)

    # -- reporting platform --
    @property
    def report_definitions(self) -> ReportDefinitionRepository:
        return self._get("report_definitions", ReportDefinitionRepository)

    @property
    def report_runs(self) -> ReportRunRepository:
        return self._get("report_runs", ReportRunRepository)

    # -- forecasting engine --
    @property
    def forecast_jobs(self) -> ForecastJobRepository:
        return self._get("forecast_jobs", ForecastJobRepository)

    # -- recommendation engine --
    @property
    def recommendations(self) -> RecommendationRepository:
        return self._get("recommendations", RecommendationRepository)

    # -- visualization / dashboard platform --
    @property
    def dashboards(self) -> DashboardRepository:
        return self._get("dashboards", DashboardRepository)

    @property
    def dashboard_widgets(self) -> DashboardWidgetRepository:
        return self._get("dashboard_widgets", DashboardWidgetRepository)

    @property
    def saved_views(self) -> SavedViewRepository:
        return self._get("saved_views", SavedViewRepository)

    # -- security / governance --
    @property
    def role_grants(self) -> AnalyticsRoleGrantRepository:
        return self._get("role_grants", AnalyticsRoleGrantRepository)

    @property
    def row_level_rules(self) -> RowLevelSecurityRuleRepository:
        return self._get("row_level_rules", RowLevelSecurityRuleRepository)

    @property
    def column_level_rules(self) -> ColumnLevelSecurityRuleRepository:
        return self._get("column_level_rules", ColumnLevelSecurityRuleRepository)

    @property
    def audit_log(self) -> AuditLogEntryRepository:
        return self._get("audit_log", AuditLogEntryRepository)

    @property
    def data_lineage_edges(self) -> DataLineageEdgeRepository:
        return self._get("data_lineage_edges", DataLineageEdgeRepository)

    # -- observability --
    @property
    def usage_events(self) -> UsageEventRepository:
        return self._get("usage_events", UsageEventRepository)

    @property
    def query_performance(self) -> QueryPerformanceRepository:
        return self._get("query_performance", QueryPerformanceRepository)

    @property
    def forecast_accuracy(self) -> ForecastAccuracyRepository:
        return self._get("forecast_accuracy", ForecastAccuracyRepository)

    @property
    def recommendation_outcomes(self) -> RecommendationOutcomeRepository:
        return self._get("recommendation_outcomes", RecommendationOutcomeRepository)

    # -- exports --
    @property
    def export_jobs(self) -> DataExportJobRepository:
        return self._get("export_jobs", DataExportJobRepository)
