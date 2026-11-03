"""On-demand report generation. Every report is computed fresh from the
underlying data at generation time and then persisted as a point-in-time
snapshot (`ReportModel.result`) — distinct from a dashboard, which is
always live (see `dashboards/dashboard_service.py`'s docstring). A
report you generated yesterday should still read the same today even
if the underlying data has since changed; a dashboard should not."""
from __future__ import annotations

from datetime import datetime, timedelta

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import ValidationError
from observability_platform.database.base import utcnow
from observability_platform.domain.entities import _aware
from observability_platform.domain.enums import ReportType
from observability_platform.logs.search_service import LogSearchService
from observability_platform.metrics.query_service import MetricQueryService
from observability_platform.models.reporting import ReportModel
from observability_platform.repositories.registry import RepositoryRegistry


class ReportService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.log_search = LogSearchService(repos)
        self.metric_query = MetricQueryService(repos)

    async def generate_report(
        self,
        tenant_id: str,
        report_type: str,
        *,
        title: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        params: dict | None = None,
        generated_by: str | None = None,
    ) -> ReportModel:
        if report_type not in {t.value for t in ReportType}:
            raise ValidationError(f"Unknown report type '{report_type}'")
        period_end = period_end or utcnow()
        period_start = period_start or (period_end - timedelta(days=self.settings.report_default_lookback_days))
        params = params or {}

        report = ReportModel(
            tenant_id=tenant_id, report_type=report_type, status="generating",
            title=title or f"{report_type} report", params=params,
            period_start=period_start, period_end=period_end, generated_by=generated_by,
        )
        report = await self.repos.reports.add(report)

        builders = {
            ReportType.AVAILABILITY.value: self._build_availability,
            ReportType.PERFORMANCE.value: self._build_performance,
            ReportType.INCIDENT.value: self._build_incident,
            ReportType.SLA.value: self._build_sla,
            ReportType.ERROR.value: self._build_error,
            ReportType.CAPACITY.value: self._build_capacity,
            ReportType.USAGE.value: self._build_usage,
            ReportType.TREND.value: self._build_trend,
            ReportType.COMPLIANCE.value: self._build_compliance,
        }
        try:
            result = await builders[report_type](tenant_id, period_start, period_end, params)
            report.result = result
            report.status = "ready"
            report.generated_at = utcnow()
        except Exception as exc:
            report.status = "failed"
            report.error_message = str(exc)
        return await self.repos.reports.update(report)

    async def _build_availability(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        components = await self.repos.components.list_for_tenant(tenant_id)
        availability: dict[str, float] = {}
        for component in components:
            history = await self.repos.health_check_results.history_for_component(tenant_id, component.id, limit=10000)
            in_window = [h for h in history if start <= _aware(h.checked_at) <= end]
            if not in_window:
                continue
            healthy_count = sum(1 for h in in_window if h.status == "healthy")
            availability[component.name] = round(healthy_count / len(in_window) * 100, 2)
        return {"availability_pct_by_component": availability}

    async def _build_performance(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        metric_name = params.get("metric_name", "api_latency_ms")
        agg = await self.metric_query.aggregate_range(tenant_id, metric_name, start_time=start, end_time=end)
        return {"metric_name": metric_name, **agg.__dict__}

    async def _build_incident(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        incidents = await self.repos.incidents.list_by_status(tenant_id, "closed", limit=10000)
        in_window = [i for i in incidents if i.detected_at and start <= _aware(i.detected_at) <= end]
        resolution_times = [
            (i.resolved_at - i.detected_at).total_seconds() / 60 for i in in_window if i.resolved_at
        ]
        mttr_minutes = round(sum(resolution_times) / len(resolution_times), 2) if resolution_times else None
        return {
            "incident_count": len(in_window),
            "by_severity": await self.repos.incidents.count_by_severity(tenant_id),
            "mean_time_to_resolve_minutes": mttr_minutes,
        }

    async def _build_sla(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        sla_minutes = params.get("sla_minutes", 60)
        incidents = await self.repos.incidents.list_by_status(tenant_id, "closed", limit=10000)
        in_window = [i for i in incidents if i.detected_at and start <= _aware(i.detected_at) <= end and i.resolved_at]
        if not in_window:
            return {"sla_minutes": sla_minutes, "compliance_pct": None, "incident_count": 0}
        within_sla = sum(1 for i in in_window if (i.resolved_at - i.detected_at).total_seconds() / 60 <= sla_minutes)
        return {
            "sla_minutes": sla_minutes,
            "compliance_pct": round(within_sla / len(in_window) * 100, 2),
            "incident_count": len(in_window),
        }

    async def _build_error(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        counts = await self.log_search.level_counts(tenant_id, start_time=start, end_time=end)
        return {"log_level_counts": counts, "error_count": counts.get("error", 0) + counts.get("critical", 0)}

    async def _build_capacity(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        resource_type = params.get("resource_type", "storage")
        history = await self.repos.capacity_snapshots.history(tenant_id, resource_type, since=start)
        return {
            "resource_type": resource_type,
            "sample_count": len(history),
            "latest_value": history[-1].value if history else None,
        }

    async def _build_usage(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        log_count = await self.log_search.total_count(tenant_id, start_time=start, end_time=end)
        metric_count = await self.repos.metric_points.count_total(tenant_id, start_time=start, end_time=end)
        return {"log_entries": log_count, "metric_points": metric_count}

    async def _build_trend(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        """Compares the requested period against the immediately
        preceding period of equal length — a simple period-over-period
        trend, not a full time-series decomposition."""
        window = end - start
        prev_start, prev_end = start - window, start
        current_errors = (await self.log_search.level_counts(tenant_id, start_time=start, end_time=end)).get("error", 0)
        previous_errors = (await self.log_search.level_counts(tenant_id, start_time=prev_start, end_time=prev_end)).get("error", 0)
        delta_pct = None
        if previous_errors:
            delta_pct = round((current_errors - previous_errors) / previous_errors * 100, 2)
        return {"current_period_errors": current_errors, "previous_period_errors": previous_errors, "change_pct": delta_pct}

    async def _build_compliance(self, tenant_id: str, start: datetime, end: datetime, params: dict) -> dict:
        policies = await self.repos.retention_policies.list_for_tenant(tenant_id)
        audit_entries = await self.repos.audit_log_entries.list_for_tenant(tenant_id, limit=10000)
        in_window = [a for a in audit_entries if start <= _aware(a.occurred_at) <= end]
        return {
            "retention_policies": [{"resource_type": p.resource_type, "retention_days": p.retention_days} for p in policies],
            "audit_event_count_in_period": len(in_window),
        }
