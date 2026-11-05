"""RepositoryRegistry: wires every repository to one shared AsyncSession,
so a single unit-of-work-scoped session backs every repository an
application-service call touches. Same pattern as every other AIOS
services's `RepositoryRegistry`."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from observability_platform.repositories.alert_repository import (
    AlertEscalationRepository,
    AlertNotificationRepository,
    AlertRepository,
    AlertRuleRepository,
    EscalationPolicyRepository,
    MaintenanceWindowRepository,
    NotificationChannelRepository,
)
from observability_platform.repositories.capacity_repository import CapacityForecastRepository, CapacitySnapshotRepository
from observability_platform.repositories.component_repository import ComponentRepository
from observability_platform.repositories.dashboard_repository import DashboardRepository
from observability_platform.repositories.governance_repository import (
    AccessGrantRepository,
    AuditLogEntryRepository,
    RetentionPolicyRepository,
)
from observability_platform.repositories.health_repository import HealthCheckResultRepository
from observability_platform.repositories.incident_repository import (
    IncidentPostmortemRepository,
    IncidentRepository,
    IncidentTimelineEventRepository,
)
from observability_platform.repositories.log_repository import LogEntryRepository
from observability_platform.repositories.metric_repository import MetricDefinitionRepository, MetricPointRepository
from observability_platform.repositories.report_repository import ReportRepository
from observability_platform.repositories.topology_repository import TopologyEdgeRepository, TopologyNodeRepository
from observability_platform.repositories.trace_repository import SpanRepository, TraceRepository


class RepositoryRegistry:
    """One instance per unit-of-work session; exposes every repository as
    a lazily-constructed, memoized property so services only pay for the
    repositories they actually touch."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    # -- components ---------------------------------------------------------------
    @property
    def components(self) -> ComponentRepository:
        return self._get("components", ComponentRepository)

    # -- logging ------------------------------------------------------------------
    @property
    def log_entries(self) -> LogEntryRepository:
        return self._get("log_entries", LogEntryRepository)

    # -- metrics -------------------------------------------------------------------
    @property
    def metric_definitions(self) -> MetricDefinitionRepository:
        return self._get("metric_definitions", MetricDefinitionRepository)

    @property
    def metric_points(self) -> MetricPointRepository:
        return self._get("metric_points", MetricPointRepository)

    # -- tracing -------------------------------------------------------------------
    @property
    def traces(self) -> TraceRepository:
        return self._get("traces", TraceRepository)

    @property
    def spans(self) -> SpanRepository:
        return self._get("spans", SpanRepository)

    # -- health ---------------------------------------------------------------------
    @property
    def health_check_results(self) -> HealthCheckResultRepository:
        return self._get("health_check_results", HealthCheckResultRepository)

    # -- alerts -----------------------------------------------------------------------
    @property
    def alert_rules(self) -> AlertRuleRepository:
        return self._get("alert_rules", AlertRuleRepository)

    @property
    def alerts(self) -> AlertRepository:
        return self._get("alerts", AlertRepository)

    @property
    def escalation_policies(self) -> EscalationPolicyRepository:
        return self._get("escalation_policies", EscalationPolicyRepository)

    @property
    def alert_escalations(self) -> AlertEscalationRepository:
        return self._get("alert_escalations", AlertEscalationRepository)

    @property
    def maintenance_windows(self) -> MaintenanceWindowRepository:
        return self._get("maintenance_windows", MaintenanceWindowRepository)

    @property
    def notification_channels(self) -> NotificationChannelRepository:
        return self._get("notification_channels", NotificationChannelRepository)

    @property
    def alert_notifications(self) -> AlertNotificationRepository:
        return self._get("alert_notifications", AlertNotificationRepository)

    # -- incidents ----------------------------------------------------------------------
    @property
    def incidents(self) -> IncidentRepository:
        return self._get("incidents", IncidentRepository)

    @property
    def incident_timeline_events(self) -> IncidentTimelineEventRepository:
        return self._get("incident_timeline_events", IncidentTimelineEventRepository)

    @property
    def incident_postmortems(self) -> IncidentPostmortemRepository:
        return self._get("incident_postmortems", IncidentPostmortemRepository)

    # -- capacity -------------------------------------------------------------------------
    @property
    def capacity_snapshots(self) -> CapacitySnapshotRepository:
        return self._get("capacity_snapshots", CapacitySnapshotRepository)

    @property
    def capacity_forecasts(self) -> CapacityForecastRepository:
        return self._get("capacity_forecasts", CapacityForecastRepository)

    # -- topology --------------------------------------------------------------------------
    @property
    def topology_nodes(self) -> TopologyNodeRepository:
        return self._get("topology_nodes", TopologyNodeRepository)

    @property
    def topology_edges(self) -> TopologyEdgeRepository:
        return self._get("topology_edges", TopologyEdgeRepository)

    # -- dashboards / reporting --------------------------------------------------------------
    @property
    def dashboards(self) -> DashboardRepository:
        return self._get("dashboards", DashboardRepository)

    @property
    def reports(self) -> ReportRepository:
        return self._get("reports", ReportRepository)

    # -- governance ---------------------------------------------------------------------------
    @property
    def access_grants(self) -> AccessGrantRepository:
        return self._get("access_grants", AccessGrantRepository)

    @property
    def audit_log_entries(self) -> AuditLogEntryRepository:
        return self._get("audit_log_entries", AuditLogEntryRepository)

    @property
    def retention_policies(self) -> RetentionPolicyRepository:
        return self._get("retention_policies", RetentionPolicyRepository)
