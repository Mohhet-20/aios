"""Analytics snapshots: periodic reports across the eight report types
the prompt specifies, persisted per period rather than recomputed on
every read. `create_snapshot` takes an already-computed `data` payload
-- this service owns the storage/retrieval/retention contract, not the
aggregation logic that produces the numbers (that lives wherever the
caller assembles the report, e.g. from `GatewayMetricsService` and
`DependencyTopologyService`)."""
from __future__ import annotations

from datetime import datetime, timedelta

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import MetricNotFoundError, ValidationError
from gateway_platform.database.base import utcnow
from gateway_platform.domain.enums import AnalyticsSnapshotType
from gateway_platform.models.observability import AnalyticsSnapshotModel
from gateway_platform.repositories.registry import RepositoryRegistry


class AnalyticsSnapshotService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid_type(self, snapshot_type: str) -> None:
        try:
            AnalyticsSnapshotType(snapshot_type)
        except ValueError as exc:
            raise ValidationError(f"'{snapshot_type}' is not a supported analytics snapshot type") from exc

    async def create_snapshot(
        self, tenant_id: str, *, snapshot_type: str, period_start: datetime, period_end: datetime, data: dict,
    ) -> AnalyticsSnapshotModel:
        self._assert_valid_type(snapshot_type)
        snapshot = AnalyticsSnapshotModel(
            tenant_id=tenant_id, snapshot_type=snapshot_type, period_start=period_start, period_end=period_end, data=data,
        )
        return await self.repos.analytics_snapshots.add(snapshot)

    async def list_by_type(self, tenant_id: str, snapshot_type: str, *, limit: int = 50) -> list[AnalyticsSnapshotModel]:
        return await self.repos.analytics_snapshots.list_by_type(tenant_id, snapshot_type, limit=limit)

    async def latest(self, tenant_id: str, snapshot_type: str) -> AnalyticsSnapshotModel:
        snapshots = await self.list_by_type(tenant_id, snapshot_type, limit=1)
        if not snapshots:
            raise MetricNotFoundError(f"no '{snapshot_type}' analytics snapshot recorded for tenant '{tenant_id}'")
        return snapshots[0]

    async def sweep_retention(self, tenant_id: str) -> int:
        cutoff = utcnow() - timedelta(days=self.settings.analytics_retention_days)
        return await self.repos.analytics_snapshots.delete_older_than(tenant_id, cutoff)
