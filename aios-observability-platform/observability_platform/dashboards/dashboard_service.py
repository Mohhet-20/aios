"""Dashboards store layout/widget *configuration* only (see
`models/dashboards.py`'s docstring) — `render` is where the actual
numbers come from, computed fresh on every call by delegating straight
into the health/alerts/incidents/capacity/logs/tracing services. A
dashboard can never show stale data because nothing about its content
is ever cached; the only persisted state is which widgets a user chose
to see and how they're arranged."""
from __future__ import annotations

from observability_platform.analytics.performance_service import PerformanceAnalysisService
from observability_platform.capacity.forecast_service import CapacityForecastService
from observability_platform.core.exceptions import DashboardError, ValidationError
from observability_platform.domain.enums import DashboardType
from observability_platform.health.aggregation_service import HealthAggregationService
from observability_platform.logs.search_service import LogSearchService
from observability_platform.models.dashboards import DashboardModel
from observability_platform.repositories.registry import RepositoryRegistry

_AI_PLATFORM_COMPONENT_TYPES = {"model", "prompt_platform", "memory_platform", "tool_platform", "agent"}


class DashboardService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.health = HealthAggregationService(repos)
        self.performance = PerformanceAnalysisService(repos)
        self.capacity = CapacityForecastService(repos)
        self.log_search = LogSearchService(repos)

    async def create_dashboard(
        self,
        tenant_id: str,
        *,
        name: str,
        dashboard_type: str,
        owner: str | None = None,
        layout: dict | None = None,
        widgets: list | None = None,
        is_default: bool = False,
    ) -> DashboardModel:
        if dashboard_type not in {t.value for t in DashboardType}:
            raise ValidationError(f"Unknown dashboard type '{dashboard_type}'")
        dashboard = DashboardModel(
            tenant_id=tenant_id, name=name, dashboard_type=dashboard_type, owner=owner,
            layout=layout or {}, widgets=widgets or [], is_default=is_default,
        )
        return await self.repos.dashboards.add(dashboard)

    async def update_widgets(self, tenant_id: str, dashboard_id: str, widgets: list) -> DashboardModel:
        dashboard = await self.repos.dashboards.get_or_404(dashboard_id)
        dashboard.widgets = widgets
        return await self.repos.dashboards.update(dashboard)

    async def list_dashboards(self, tenant_id: str, *, dashboard_type: str | None = None) -> list[DashboardModel]:
        return await self.repos.dashboards.list_for_tenant(tenant_id, dashboard_type=dashboard_type)

    async def render(self, tenant_id: str, dashboard_id: str) -> dict:
        dashboard = await self.repos.dashboards.get_or_404(dashboard_id)
        renderers = {
            DashboardType.EXECUTIVE.value: self._render_executive,
            DashboardType.OPERATIONS.value: self._render_operations,
            DashboardType.INFRASTRUCTURE.value: self._render_infrastructure,
            DashboardType.APPLICATION.value: self._render_application,
            DashboardType.AI_PLATFORM.value: self._render_ai_platform,
            DashboardType.WORKFLOW.value: self._render_workflow,
            DashboardType.DATABASE.value: self._render_database,
            DashboardType.SECURITY.value: self._render_security,
            DashboardType.INCIDENT.value: self._render_incident,
            DashboardType.CAPACITY.value: self._render_capacity,
        }
        renderer = renderers.get(dashboard.dashboard_type)
        if renderer is None:
            raise DashboardError(f"No renderer registered for dashboard type '{dashboard.dashboard_type}'")
        return {
            "dashboard_id": dashboard.id,
            "name": dashboard.name,
            "dashboard_type": dashboard.dashboard_type,
            "widgets": await renderer(tenant_id),
        }

    async def _render_executive(self, tenant_id: str) -> dict:
        overall = await self.health.overall_system_health(tenant_id)
        incident_counts = await self.repos.incidents.count_by_severity(tenant_id)
        alert_counts = await self.repos.alerts.count_by_status(tenant_id)
        return {"system_health": overall, "incidents_by_severity": incident_counts, "alerts_by_status": alert_counts}

    async def _render_operations(self, tenant_id: str) -> dict:
        alert_counts = await self.repos.alerts.count_by_status(tenant_id)
        open_incidents = await self.repos.incidents.list_open(tenant_id)
        overall = await self.health.overall_system_health(tenant_id)
        return {
            "alerts_by_status": alert_counts,
            "open_incident_count": len(open_incidents),
            "system_health": overall["overall_status"],
        }

    async def _render_infrastructure(self, tenant_id: str) -> dict:
        return {"health_by_component_type": await self.health.health_by_component_type(tenant_id)}

    async def _render_application(self, tenant_id: str) -> dict:
        return {"log_level_counts": await self.log_search.level_counts(tenant_id)}

    async def _render_ai_platform(self, tenant_id: str) -> dict:
        by_type = await self.health.health_by_component_type(tenant_id)
        return {"ai_component_health": {k: v for k, v in by_type.items() if k in _AI_PLATFORM_COMPONENT_TYPES}}

    async def _render_workflow(self, tenant_id: str) -> dict:
        return {"workflow_step_performance": await self.performance.performance_by_span_kind(tenant_id, "workflow_step")}

    async def _render_database(self, tenant_id: str) -> dict:
        return {
            "database_query_performance": await self.performance.performance_by_span_kind(tenant_id, "database_query"),
            "slow_queries": await self.performance.slow_query_analysis(tenant_id),
        }

    async def _render_security(self, tenant_id: str) -> dict:
        recent_audit = await self.repos.audit_log_entries.list_for_tenant(tenant_id, limit=50)
        alert_counts_by_status = await self.repos.alerts.count_by_status(tenant_id)
        return {
            "recent_audit_events": [{"action": a.action, "occurred_at": a.occurred_at.isoformat()} for a in recent_audit],
            "alerts_by_status": alert_counts_by_status,
        }

    async def _render_incident(self, tenant_id: str) -> dict:
        return {
            "open_incidents": [
                {"id": i.id, "title": i.title, "severity": i.severity, "status": i.status}
                for i in await self.repos.incidents.list_open(tenant_id)
            ],
            "incidents_by_severity": await self.repos.incidents.count_by_severity(tenant_id),
        }

    async def _render_capacity(self, tenant_id: str) -> dict:
        forecasts = {}
        for resource_type in ("storage", "traffic", "cpu", "memory", "cost", "concurrent_users"):
            latest = await self.repos.capacity_forecasts.latest_for_resource(tenant_id, resource_type)
            if latest is not None:
                forecasts[resource_type] = {"horizon_days": latest.horizon_days, "points": latest.points}
        return {"forecasts": forecasts}
