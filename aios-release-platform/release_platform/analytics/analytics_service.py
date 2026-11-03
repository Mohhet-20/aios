"""Observability & Release Analytics: raw deployment metric events
(success/failure, duration, rollback triggers, failed releases) plus
periodic version-adoption snapshots. Split into two small services —
`DeploymentMetricService` for the event stream and its aggregations,
`AdoptionSnapshotService` for the periodic-snapshot side — mirroring
the granularity split `docs_platform.analytics` uses between its
event/feedback/broken-link services."""
from __future__ import annotations

from release_platform.analytics.aggregation_rules import (
    average_deployment_duration,
    deployment_success_rate,
    failed_release_count,
    rollback_frequency,
)
from release_platform.core.exceptions import ValidationError
from release_platform.models.analytics import DeploymentMetricModel, ReleaseAdoptionSnapshotModel
from release_platform.repositories.registry import RepositoryRegistry

_VALID_METRIC_TYPES = {
    "deployment_succeeded", "deployment_failed", "deployment_duration_seconds",
    "rollback_triggered", "release_failed", "environment_health_score",
}


class DeploymentMetricService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_metric(self, tenant_id: str, *, metric_type: str, value: float = 0.0, deployment_id: str | None = None) -> DeploymentMetricModel:
        if metric_type not in _VALID_METRIC_TYPES:
            raise ValidationError(f"Unsupported metric_type '{metric_type}'")
        metric = DeploymentMetricModel(tenant_id=tenant_id, deployment_id=deployment_id, metric_type=metric_type, value=value)
        return await self.repos.deployment_metrics.add(metric)

    async def deployment_success_rate(self, tenant_id: str) -> float | None:
        metrics = await self.repos.deployment_metrics.list_for_tenant(tenant_id)
        return deployment_success_rate(metrics)

    async def rollback_frequency(self, tenant_id: str) -> float | None:
        metrics = await self.repos.deployment_metrics.list_for_tenant(tenant_id)
        return rollback_frequency(metrics)

    async def average_deployment_duration(self, tenant_id: str) -> float | None:
        metrics = await self.repos.deployment_metrics.list_for_tenant(tenant_id, metric_type="deployment_duration_seconds")
        return average_deployment_duration(metrics)

    async def failed_release_count(self, tenant_id: str) -> int:
        metrics = await self.repos.deployment_metrics.list_for_tenant(tenant_id, metric_type="release_failed")
        return failed_release_count(metrics)


class AdoptionSnapshotService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_snapshot(self, tenant_id: str, *, version: str, adoption_pct: float) -> ReleaseAdoptionSnapshotModel:
        if not (0.0 <= adoption_pct <= 100.0):
            raise ValidationError("adoption_pct must be between 0 and 100")
        snapshot = ReleaseAdoptionSnapshotModel(tenant_id=tenant_id, version=version, adoption_pct=adoption_pct)
        return await self.repos.adoption_snapshots.add(snapshot)

    async def list_for_version(self, tenant_id: str, version: str) -> list[ReleaseAdoptionSnapshotModel]:
        return await self.repos.adoption_snapshots.list_for_version(tenant_id, version)

    async def latest_adoption(self, tenant_id: str, version: str) -> float | None:
        snapshots = await self.list_for_version(tenant_id, version)
        if not snapshots:
            return None
        return snapshots[-1].adoption_pct
