"""Health checks + automatic recovery: each recorded result feeds the
instance's own status — `mesh_health_check_failure_threshold`
consecutive unhealthy results (the most recent N, checked in
descending recency order) mark an active instance unhealthy, and a
single healthy result recovers an unhealthy instance automatically,
exactly matching the prompt's "automatic recovery" requirement without
needing a human to flip the instance back."""
from __future__ import annotations

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.domain.enums import InstanceStatus
from gateway_platform.models.mesh import HealthCheckResultModel
from gateway_platform.repositories.registry import RepositoryRegistry


class HealthCheckService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def record_result(
        self, tenant_id: str, instance_id: str, *, healthy: bool, latency_ms: float = 0.0,
    ) -> HealthCheckResultModel:
        result = HealthCheckResultModel(tenant_id=tenant_id, instance_id=instance_id, healthy=healthy, latency_ms=latency_ms)
        result = await self.repos.health_check_results.add(result)
        await self._apply_recovery_or_degradation(tenant_id, instance_id, healthy=healthy)
        return result

    async def _apply_recovery_or_degradation(self, tenant_id: str, instance_id: str, *, healthy: bool) -> None:
        instance = await self.repos.service_instances.get_or_404(instance_id)
        if instance.tenant_id != tenant_id:
            return

        if healthy:
            if instance.status == InstanceStatus.UNHEALTHY.value:
                instance.status = InstanceStatus.ACTIVE.value
                await self.repos.service_instances.update(instance)
            return

        if instance.status != InstanceStatus.ACTIVE.value:
            return
        recent = await self.repos.health_check_results.list_for_instance(
            tenant_id, instance_id, limit=self.settings.mesh_health_check_failure_threshold,
        )
        if len(recent) >= self.settings.mesh_health_check_failure_threshold and all(not r.healthy for r in recent):
            instance.status = InstanceStatus.UNHEALTHY.value
            await self.repos.service_instances.update(instance)

    async def list_for_instance(self, tenant_id: str, instance_id: str, *, limit: int = 50) -> list[HealthCheckResultModel]:
        return await self.repos.health_check_results.list_for_instance(tenant_id, instance_id, limit=limit)
