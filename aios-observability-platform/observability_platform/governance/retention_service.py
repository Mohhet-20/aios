"""Cross-cutting retention sweep orchestrator. Every high-volume
telemetry table (logs, metrics, traces/spans) plus the audit log has
its own per-resource-type retention policy lookup already (see
`logs/retention_service.py`, `governance/audit_service.py`) — this
service is the single entry point a scheduler calls once per tenant to
sweep all of them together, rather than four separate cron entries
that could drift out of sync."""
from __future__ import annotations

from datetime import timedelta

from observability_platform.config.settings import Settings, get_settings
from observability_platform.database.base import utcnow
from observability_platform.governance.audit_service import AuditService
from observability_platform.logs.retention_service import LogRetentionService
from observability_platform.repositories.registry import RepositoryRegistry


class RetentionOrchestrationService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.logs = LogRetentionService(repos, settings=self.settings)
        self.audit = AuditService(repos, settings=self.settings)

    async def _retention_days(self, tenant_id: str, resource_type: str, default_days: int) -> int:
        policy = await self.repos.retention_policies.get_for_resource(tenant_id, resource_type)
        if policy is not None and policy.is_enabled:
            return policy.retention_days
        return default_days

    async def sweep_metrics(self, tenant_id: str) -> int:
        retention_days = await self._retention_days(tenant_id, "metrics", self.settings.metric_retention_days)
        cutoff = utcnow() - timedelta(days=retention_days)
        return await self.repos.metric_points.delete_older_than(tenant_id, cutoff)

    async def sweep_traces(self, tenant_id: str) -> dict:
        retention_days = await self._retention_days(tenant_id, "traces", self.settings.trace_retention_days)
        cutoff = utcnow() - timedelta(days=retention_days)
        deleted_spans = await self.repos.spans.delete_older_than(tenant_id, cutoff)
        deleted_traces = await self.repos.traces.delete_older_than(tenant_id, cutoff)
        return {"spans_deleted": deleted_spans, "traces_deleted": deleted_traces}

    async def sweep_all(self, tenant_id: str) -> dict:
        return {
            "logs_deleted": await self.logs.sweep_expired(tenant_id),
            "metric_points_deleted": await self.sweep_metrics(tenant_id),
            **await self.sweep_traces(tenant_id),
            "audit_entries_deleted": await self.audit.sweep_expired(tenant_id),
        }
