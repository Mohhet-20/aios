"""Raw reliability metric snapshot recording (availability,
reliability, durability, error budget, MTTD, MTTR, MTBF, recovery
success rate) — the time series `SloService.evaluate_slo` reads its
latest "availability" reading from."""
from __future__ import annotations

from quality_platform.core.exceptions import UnsupportedReliabilityMetricError
from quality_platform.domain.enums import ReliabilityMetricType
from quality_platform.models.reliability import ReliabilityMetricSnapshotModel
from quality_platform.repositories.registry import RepositoryRegistry

_VALID_METRIC_TYPES = {m.value for m in ReliabilityMetricType}


class ReliabilitySnapshotService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_snapshot(self, tenant_id: str, service_ref: str, *, metric_type: str, value: float) -> ReliabilityMetricSnapshotModel:
        if metric_type not in _VALID_METRIC_TYPES:
            raise UnsupportedReliabilityMetricError(f"Unsupported reliability metric type '{metric_type}'")
        snapshot = ReliabilityMetricSnapshotModel(tenant_id=tenant_id, service_ref=service_ref, metric_type=metric_type, value=value)
        return await self.repos.reliability_snapshots.add(snapshot)

    async def list_for_service(self, tenant_id: str, service_ref: str, *, metric_type: str | None = None, limit: int = 500) -> list[ReliabilityMetricSnapshotModel]:
        return await self.repos.reliability_snapshots.list_for_service(tenant_id, service_ref, metric_type=metric_type, limit=limit)

    async def latest_value(self, tenant_id: str, service_ref: str, metric_type: str) -> float | None:
        recent = await self.list_for_service(tenant_id, service_ref, metric_type=metric_type, limit=1)
        return recent[0].value if recent else None
