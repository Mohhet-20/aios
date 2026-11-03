"""Metric ingestion. Registers a `MetricDefinitionModel` the first time
a given metric name is seen for a tenant (idempotent — a second
registration for the same name is a no-op, not an error) and then
appends a `MetricPointModel` sample.

`HighCardinalityError` is a deliberately simple guard: it counts the
number of *label keys* on one point, not the number of distinct
label-value combinations seen historically (a true cardinality check
needs either a running distinct-count index or a time-windowed
approximation structure like HyperLogLog, out of scope for this
build). It still catches the most common real mistake — someone
tagging a metric with a naturally-unbounded key like a raw user id or
request id — without pretending to be a full cardinality-explosion
detector."""
from __future__ import annotations

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import HighCardinalityError, MetricBatchTooLargeError, ValidationError
from observability_platform.domain.enums import MetricType
from observability_platform.models.metrics import MetricDefinitionModel, MetricPointModel
from observability_platform.repositories.registry import RepositoryRegistry


class MetricIngestService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def _ensure_definition(
        self, tenant_id: str, name: str, metric_type: str, unit: str | None
    ) -> MetricDefinitionModel:
        existing = await self.repos.metric_definitions.get_by_name(tenant_id, name)
        if existing is not None:
            return existing
        return await self.repos.metric_definitions.add(
            MetricDefinitionModel(tenant_id=tenant_id, name=name, metric_type=metric_type, unit=unit)
        )

    async def ingest(
        self,
        tenant_id: str,
        *,
        name: str,
        metric_type: str,
        value: float,
        unit: str | None = None,
        labels: dict | None = None,
        component_id: str | None = None,
        service_name: str | None = None,
    ) -> MetricPointModel:
        if metric_type not in {mt.value for mt in MetricType}:
            raise ValidationError(f"Unknown metric type '{metric_type}'")
        labels = labels or {}
        if len(labels) > self.settings.metric_high_cardinality_label_limit:
            raise HighCardinalityError(
                f"Metric '{name}' has {len(labels)} label keys, exceeding the limit of "
                f"{self.settings.metric_high_cardinality_label_limit}"
            )
        await self._ensure_definition(tenant_id, name, metric_type, unit)
        point = MetricPointModel(
            tenant_id=tenant_id, metric_name=name, metric_type=metric_type, value=value, unit=unit,
            labels=labels, component_id=component_id, service_name=service_name,
        )
        return await self.repos.metric_points.add(point)

    async def ingest_batch(self, tenant_id: str, points: list[dict]) -> list[MetricPointModel]:
        if len(points) > self.settings.metric_ingest_max_batch:
            raise MetricBatchTooLargeError(
                f"Batch of {len(points)} exceeds max batch size of {self.settings.metric_ingest_max_batch}"
            )
        return [await self.ingest(tenant_id, **p) for p in points]
