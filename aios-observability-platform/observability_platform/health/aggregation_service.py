"""System-wide health rollup: takes every registered component's
current (derived, never cached) status and reduces it to one overall
system status by taking the worst rank present — one UNHEALTHY
component means the system-wide rollup is UNHEALTHY, matching how a
human on-call would summarize "is everything okay?" """
from __future__ import annotations

from observability_platform.domain.enums import HealthStatus
from observability_platform.health.healthcheck_service import HealthCheckService
from observability_platform.repositories.registry import RepositoryRegistry


class HealthAggregationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.healthcheck_service = HealthCheckService(repos)

    async def overall_system_health(self, tenant_id: str) -> dict:
        components = await self.repos.components.list_for_tenant(tenant_id)
        statuses: dict[str, HealthStatus] = {}
        for component in components:
            statuses[component.id] = await self.healthcheck_service.current_status(tenant_id, component.id)

        worst = max((s.rank for s in statuses.values()), default=HealthStatus.UNKNOWN.rank)
        overall = next((s for s in HealthStatus if s.rank == worst), HealthStatus.UNKNOWN)
        return {
            "overall_status": overall.value,
            "component_count": len(components),
            "component_statuses": {cid: s.value for cid, s in statuses.items()},
        }

    async def health_by_component_type(self, tenant_id: str) -> dict[str, dict]:
        components = await self.repos.components.list_for_tenant(tenant_id)
        by_type: dict[str, list] = {}
        for component in components:
            by_type.setdefault(component.component_type, []).append(component)

        result: dict[str, dict] = {}
        for component_type, comps in by_type.items():
            statuses = [await self.healthcheck_service.current_status(tenant_id, c.id) for c in comps]
            worst = max((s.rank for s in statuses), default=HealthStatus.UNKNOWN.rank)
            overall = next((s for s in HealthStatus if s.rank == worst), HealthStatus.UNKNOWN)
            result[component_type] = {
                "overall_status": overall.value,
                "component_count": len(comps),
            }
        return result
