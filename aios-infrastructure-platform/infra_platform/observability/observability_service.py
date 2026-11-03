"""Infra Observability: a generic time-series metric point shared by
every metric family this platform emits (infrastructure, deployment,
inference, training/model performance, cluster health, scaling
events, resource utilization) distinguished by `metric_name` /
`resource_type` / `tags` rather than one table per family, plus
cluster health check results. `deployment_success_rate` is a
read-only cross-module aggregation over the Deployment Strategies
module's own status counts — observability reads other modules'
state, it doesn't own it."""
from __future__ import annotations

from datetime import timedelta

from infra_platform.config.settings import Settings, get_settings
from infra_platform.models.observability import ClusterHealthCheckModel, InfraMetricModel
from infra_platform.repositories.registry import RepositoryRegistry
from infra_platform.clock import utc_now


class InfraMetricService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def record_metric(
        self, tenant_id: str, *, metric_name: str, value: float, unit: str | None = None,
        resource_type: str | None = None, resource_id: str | None = None, tags: dict | None = None,
    ) -> InfraMetricModel:
        metric = InfraMetricModel(
            tenant_id=tenant_id, metric_name=metric_name, value=value, unit=unit,
            resource_type=resource_type, resource_id=resource_id, tags=tags or {},
        )
        return await self.repos.infra_metrics.add(metric)

    async def list_recent(self, tenant_id: str, *, metric_name: str | None = None, limit: int = 200) -> list[InfraMetricModel]:
        return await self.repos.infra_metrics.list_recent(tenant_id, metric_name=metric_name, limit=limit)

    async def latest_for_metric(self, tenant_id: str, metric_name: str, *, resource_id: str | None = None) -> InfraMetricModel | None:
        return await self.repos.infra_metrics.latest_for_metric(tenant_id, metric_name, resource_id=resource_id)

    async def prune_old_metrics(self, tenant_id: str) -> int:
        cutoff = utc_now() - timedelta(days=self.settings.metric_retention_days)
        return await self.repos.infra_metrics.delete_older_than(tenant_id, cutoff)

    async def deployment_success_rate(self, tenant_id: str) -> dict:
        counts = await self.repos.deployments.count_by_status(tenant_id)
        succeeded = counts.get("succeeded", 0)
        terminal = succeeded + counts.get("failed", 0) + counts.get("rolled_back", 0)
        rate = succeeded / terminal if terminal else 1.0
        return {
            "rate": rate,
            "counts": counts,
            "below_threshold": rate < self.settings.deployment_success_rate_alert_threshold,
            "threshold": self.settings.deployment_success_rate_alert_threshold,
        }


class ClusterHealthService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_health_check(self, tenant_id: str, cluster_id: str, *, status: str, details: dict | None = None) -> ClusterHealthCheckModel:
        check = ClusterHealthCheckModel(tenant_id=tenant_id, cluster_id=cluster_id, status=status, details=details or {})
        return await self.repos.cluster_health_checks.add(check)

    async def latest_for_cluster(self, tenant_id: str, cluster_id: str) -> ClusterHealthCheckModel | None:
        return await self.repos.cluster_health_checks.latest_for_cluster(tenant_id, cluster_id)

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[ClusterHealthCheckModel]:
        return await self.repos.cluster_health_checks.list_for_cluster(tenant_id, cluster_id)
