"""Health monitoring. A component's "current" status is never a cached
column — it's always derived from its latest `HealthCheckResultModel`
row, recomputed on every read via `current_status`. A component with no
result yet, or whose latest result is older than
`health_stale_after_seconds`, is reported UNKNOWN rather than assumed
healthy — silence is not evidence of health, it's evidence the check
stopped running (crashed worker, network partition, etc.)."""
from __future__ import annotations

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import ComponentNotRegisteredError, ValidationError
from observability_platform.database.base import utcnow
from observability_platform.domain.enums import HealthStatus
from observability_platform.models.health import HealthCheckResultModel
from observability_platform.repositories.registry import RepositoryRegistry


class HealthCheckService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def record_result(
        self,
        tenant_id: str,
        component_id: str,
        *,
        status: str,
        message: str | None = None,
        latency_ms: float | None = None,
        metadata: dict | None = None,
    ) -> HealthCheckResultModel:
        if status not in {s.value for s in HealthStatus}:
            raise ValidationError(f"Unknown health status '{status}'")
        component = await self.repos.components.get(component_id)
        if component is None or component.tenant_id != tenant_id:
            raise ComponentNotRegisteredError(f"Component '{component_id}' is not registered for tenant '{tenant_id}'")
        result = HealthCheckResultModel(
            tenant_id=tenant_id, component_id=component_id, status=status, message=message,
            latency_ms=latency_ms, check_metadata=metadata or {},
        )
        return await self.repos.health_check_results.add(result)

    async def current_status(self, tenant_id: str, component_id: str) -> HealthStatus:
        latest = await self.repos.health_check_results.latest_for_component(tenant_id, component_id)
        if latest is None:
            return HealthStatus.UNKNOWN
        age_seconds = (utcnow() - _aware(latest.checked_at)).total_seconds()
        if age_seconds > self.settings.health_stale_after_seconds:
            return HealthStatus.UNKNOWN
        return HealthStatus(latest.status)

    async def history(self, tenant_id: str, component_id: str, *, limit: int = 100) -> list[HealthCheckResultModel]:
        return await self.repos.health_check_results.history_for_component(tenant_id, component_id, limit=limit)


def _aware(dt):
    from datetime import timezone

    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
