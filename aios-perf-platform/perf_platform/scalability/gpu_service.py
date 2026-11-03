"""GPU pool inventory & utilization tracking. This platform models the
scheduling/sharing/autoscaling *architecture* (pool types, per-pool
utilization, activate/deactivate) — see README disclosed scope
boundaries for what a real GPU scheduler integration would add."""
from __future__ import annotations

from perf_platform.config.settings import get_settings
from perf_platform.core.exceptions import GpuPoolNotFoundError, UnsupportedGpuPoolTypeError
from perf_platform.models.scalability import GpuPoolModel
from perf_platform.repositories.registry import RepositoryRegistry


class GpuPoolService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, pool_id: str) -> GpuPoolModel:
        pool = await self.repos.gpu_pools.get_or_404(pool_id)
        if pool.tenant_id != tenant_id:
            raise GpuPoolNotFoundError(f"GpuPool '{pool_id}' not found for tenant '{tenant_id}'")
        return pool

    async def register_pool(self, tenant_id: str, *, name: str, pool_type: str, gpu_count: int = 1) -> GpuPoolModel:
        if pool_type not in self.settings.gpu_pool_types:
            raise UnsupportedGpuPoolTypeError(f"Unsupported GPU pool type '{pool_type}'")
        existing = await self.repos.gpu_pools.get_by_name(tenant_id, name)
        if existing is not None:
            return existing
        pool = await self.repos.gpu_pools.add(GpuPoolModel(tenant_id=tenant_id, name=name, pool_type=pool_type, gpu_count=gpu_count))
        await self.repos.session.commit()
        return pool

    async def report_utilization(self, tenant_id: str, pool_id: str, utilization_pct: float) -> GpuPoolModel:
        pool = await self.get_or_404(tenant_id, pool_id)
        pool.utilization_pct = max(0.0, min(100.0, utilization_pct))
        await self.repos.session.commit()
        return pool

    async def deactivate(self, tenant_id: str, pool_id: str) -> GpuPoolModel:
        pool = await self.get_or_404(tenant_id, pool_id)
        pool.is_active = False
        await self.repos.session.commit()
        return pool

    async def activate(self, tenant_id: str, pool_id: str) -> GpuPoolModel:
        pool = await self.get_or_404(tenant_id, pool_id)
        pool.is_active = True
        await self.repos.session.commit()
        return pool

    async def list_for_tenant(self, tenant_id: str, *, pool_type: str | None = None) -> list[GpuPoolModel]:
        return await self.repos.gpu_pools.list_for_tenant(tenant_id, pool_type=pool_type)

    async def underutilized_pools(self, tenant_id: str, *, threshold_pct: float = 20.0) -> list[GpuPoolModel]:
        """Pools running hot enough capacity to be a cost-reduction
        candidate (scale down / consolidate) — the auto-optimization
        engine's `infrastructure`/`scaling` recommendations would read
        from this in a fuller integration; kept as a direct query here
        since it's a simple threshold filter, not a rule worth its own
        pure-function module."""
        pools = await self.repos.gpu_pools.list_for_tenant(tenant_id, pool_type=None)
        return [p for p in pools if p.is_active and p.utilization_pct < threshold_pct]
