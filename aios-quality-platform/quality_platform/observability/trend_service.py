"""Trend snapshot recording/querying across the eight metric types the
prompt specifies — the time series every quality/regression/coverage/
failure/performance/reliability/release dashboard in this platform
reads from. `direction_for` layers `trend_rules.compute_trend_direction`
on top of the stored series."""
from __future__ import annotations

from quality_platform.core.exceptions import ObservabilityError
from quality_platform.domain.enums import TrendMetricType
from quality_platform.models.observability import TrendSnapshotModel
from quality_platform.observability.trend_rules import compute_trend_direction
from quality_platform.repositories.registry import RepositoryRegistry

_VALID_METRIC_TYPES = {m.value for m in TrendMetricType}


class TrendService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_snapshot(self, tenant_id: str, *, metric_type: str, value: float, subject_ref: str | None = None) -> TrendSnapshotModel:
        if metric_type not in _VALID_METRIC_TYPES:
            raise ObservabilityError(f"Unsupported trend metric type '{metric_type}'")
        snapshot = TrendSnapshotModel(tenant_id=tenant_id, metric_type=metric_type, subject_ref=subject_ref, value=value)
        return await self.repos.trend_snapshots.add(snapshot)

    async def list_trend(self, tenant_id: str, metric_type: str, *, subject_ref: str | None = None, limit: int = 500) -> list[TrendSnapshotModel]:
        return await self.repos.trend_snapshots.list_for_metric(tenant_id, metric_type, subject_ref=subject_ref, limit=limit)

    async def direction_for(self, tenant_id: str, metric_type: str, *, subject_ref: str | None = None, limit: int = 500) -> str:
        snapshots = await self.list_trend(tenant_id, metric_type, subject_ref=subject_ref, limit=limit)
        return compute_trend_direction([s.value for s in snapshots])
