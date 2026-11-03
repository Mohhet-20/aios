"""Gateway metrics: raw time-series sample recording across the nine
metric types the prompt specifies, plus small real aggregation helpers
(average, sum, error rate) computed over the recent-samples window
rather than a pre-aggregated rollup table -- consistent with this
platform's "genuinely functioning but deliberately simple" posture for
analytics-adjacent engines."""
from __future__ import annotations

from datetime import timedelta

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import ValidationError
from gateway_platform.database.base import utcnow
from gateway_platform.domain.enums import GatewayMetricType
from gateway_platform.models.observability import GatewayMetricModel
from gateway_platform.repositories.registry import RepositoryRegistry


class GatewayMetricsService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid_type(self, metric_type: str) -> None:
        try:
            GatewayMetricType(metric_type)
        except ValueError as exc:
            raise ValidationError(f"'{metric_type}' is not a supported gateway metric type") from exc

    async def record_metric(
        self, tenant_id: str, *, metric_type: str, value: float, route_id: str | None = None, service_id: str | None = None,
    ) -> GatewayMetricModel:
        self._assert_valid_type(metric_type)
        metric = GatewayMetricModel(
            tenant_id=tenant_id, metric_type=metric_type, value=value, route_id=route_id, service_id=service_id,
        )
        return await self.repos.gateway_metrics.add(metric)

    async def list_recent(self, tenant_id: str, *, metric_type: str | None = None, limit: int = 500) -> list[GatewayMetricModel]:
        return await self.repos.gateway_metrics.list_recent(tenant_id, metric_type=metric_type, limit=limit)

    async def average(self, tenant_id: str, metric_type: str, *, limit: int = 500) -> float:
        samples = await self.list_recent(tenant_id, metric_type=metric_type, limit=limit)
        if not samples:
            return 0.0
        return sum(sample.value for sample in samples) / len(samples)

    async def total(self, tenant_id: str, metric_type: str, *, limit: int = 500) -> float:
        samples = await self.list_recent(tenant_id, metric_type=metric_type, limit=limit)
        return sum(sample.value for sample in samples)

    async def error_rate(self, tenant_id: str, *, limit: int = 500) -> float:
        """failures / api_calls over the recent window; 0.0 if there
        have been no recorded API calls yet, to avoid a division by
        zero implying a (misleading) 100% error rate."""
        calls = await self.total(tenant_id, GatewayMetricType.API_CALLS.value, limit=limit)
        failures = await self.total(tenant_id, GatewayMetricType.FAILURES.value, limit=limit)
        if calls <= 0:
            return 0.0
        return failures / calls

    async def sweep_retention(self, tenant_id: str) -> int:
        cutoff = utcnow() - timedelta(days=self.settings.observability_metric_retention_days)
        return await self.repos.gateway_metrics.delete_older_than(tenant_id, cutoff)
