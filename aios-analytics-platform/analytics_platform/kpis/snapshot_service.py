"""KPI snapshots: recording a value + health at a point in time, and
the trend/history reads every KPI Manager UI needs — a real historical
trend line, not just "the current number"."""
from __future__ import annotations

from analytics_platform.config.settings import Settings, get_settings
from analytics_platform.kpis.kpi_service import KpiService
from analytics_platform.models.kpis import KpiSnapshotModel
from analytics_platform.repositories.registry import RepositoryRegistry


class KpiSnapshotService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, kpi_service: KpiService | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.kpis = kpi_service or KpiService(repos)

    async def record_snapshot(self, tenant_id: str, kpi_id: str, *, value: float) -> KpiSnapshotModel:
        kpi = await self.kpis.get_or_404(tenant_id, kpi_id)
        health = self.kpis.evaluate_health(kpi, value)
        snapshot = KpiSnapshotModel(tenant_id=tenant_id, kpi_id=kpi_id, value=value, health=health)
        return await self.repos.kpi_snapshots.add(snapshot)

    async def history(self, tenant_id: str, kpi_id: str, *, limit: int = 200) -> list[KpiSnapshotModel]:
        return await self.repos.kpi_snapshots.list_for_kpi(tenant_id, kpi_id, limit=limit)

    async def trend(self, tenant_id: str, kpi_id: str) -> str:
        """Compares the oldest and newest snapshot within the recent
        window: 'up' if the value increased, 'down' if it decreased,
        'flat' if unchanged or there's fewer than two data points to
        compare."""
        snapshots = await self.history(tenant_id, kpi_id, limit=500)
        if len(snapshots) < 2:
            return "flat"
        newest = snapshots[0].value  # list_for_kpi orders newest-first
        oldest = snapshots[-1].value
        if newest > oldest:
            return "up"
        if newest < oldest:
            return "down"
        return "flat"
