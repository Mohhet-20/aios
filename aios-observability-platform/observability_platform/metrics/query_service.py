"""Metric querying: raw range fetch, latest value, whole-range
aggregation, and bucketed time-series aggregation for charting."""
from __future__ import annotations

from datetime import datetime

from observability_platform.config.settings import Settings, get_settings
from observability_platform.metrics.aggregation_service import AggregationResult, aggregate, bucketize
from observability_platform.models.metrics import MetricPointModel
from observability_platform.repositories.registry import RepositoryRegistry


class MetricQueryService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def query_range(
        self,
        tenant_id: str,
        metric_name: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        component_id: str | None = None,
    ) -> list[MetricPointModel]:
        return await self.repos.metric_points.query_range(
            tenant_id, metric_name, start_time=start_time, end_time=end_time, component_id=component_id
        )

    async def latest(self, tenant_id: str, metric_name: str, *, component_id: str | None = None) -> MetricPointModel | None:
        return await self.repos.metric_points.latest(tenant_id, metric_name, component_id=component_id)

    async def aggregate_range(
        self,
        tenant_id: str,
        metric_name: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        component_id: str | None = None,
    ) -> AggregationResult:
        points = await self.query_range(
            tenant_id, metric_name, start_time=start_time, end_time=end_time, component_id=component_id
        )
        return aggregate([p.value for p in points])

    async def time_series(
        self,
        tenant_id: str,
        metric_name: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        component_id: str | None = None,
        bucket_seconds: int | None = None,
    ) -> list[dict]:
        points = await self.query_range(
            tenant_id, metric_name, start_time=start_time, end_time=end_time, component_id=component_id
        )
        buckets = bucketize([(p.timestamp, p.value) for p in points], bucket_seconds or self.settings.metric_aggregation_bucket_seconds)
        return [
            {"bucket_start_epoch": bucket_key, **aggregate(values).__dict__}
            for bucket_key, values in sorted(buckets.items())
        ]
