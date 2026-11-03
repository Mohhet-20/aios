"""Circuit breakers: one per service, tracking closed -> open ->
half_open -> closed/open. `record_failure` trips the breaker once
`failure_count` crosses the configured threshold; `enforce` is what a
caller checks before dispatching a call, and raises
`CircuitBreakerOpenError` while open — except once
`mesh_circuit_breaker_open_seconds` has elapsed, at which point the
breaker moves itself to half_open and lets exactly one trial call
through, mirroring the classic circuit-breaker pattern."""
from __future__ import annotations

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import CircuitBreakerOpenError
from gateway_platform.database.base import utcnow
from gateway_platform.domain.entities import _aware
from gateway_platform.domain.enums import CircuitBreakerState
from gateway_platform.models.mesh import CircuitBreakerModel
from gateway_platform.repositories.registry import RepositoryRegistry
from gateway_platform.service_mesh.mappers import apply_circuit_breaker_domain_to_model, circuit_breaker_to_domain


class CircuitBreakerService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def get_or_create(self, tenant_id: str, service_id: str) -> CircuitBreakerModel:
        breaker = await self.repos.circuit_breakers.get_for_service(tenant_id, service_id)
        if breaker is not None:
            return breaker
        breaker = CircuitBreakerModel(
            tenant_id=tenant_id, service_id=service_id, state=CircuitBreakerState.CLOSED.value,
            failure_threshold=self.settings.mesh_circuit_breaker_failure_threshold,
        )
        return await self.repos.circuit_breakers.add(breaker)

    async def enforce(self, tenant_id: str, service_id: str) -> CircuitBreakerModel:
        breaker = await self.get_or_create(tenant_id, service_id)
        if breaker.state == CircuitBreakerState.OPEN.value:
            elapsed = (utcnow() - _aware(breaker.opened_at)).total_seconds()
            if elapsed >= self.settings.mesh_circuit_breaker_open_seconds:
                entity = circuit_breaker_to_domain(breaker)
                entity.half_open()
                apply_circuit_breaker_domain_to_model(entity, breaker)
                return await self.repos.circuit_breakers.update(breaker)
            raise CircuitBreakerOpenError(f"circuit breaker for service '{service_id}' is open")
        return breaker

    async def record_success(self, tenant_id: str, service_id: str) -> CircuitBreakerModel:
        breaker = await self.get_or_create(tenant_id, service_id)
        if breaker.state == CircuitBreakerState.HALF_OPEN.value:
            entity = circuit_breaker_to_domain(breaker)
            entity.close()
            apply_circuit_breaker_domain_to_model(entity, breaker)
            breaker.failure_count = 0
            return await self.repos.circuit_breakers.update(breaker)
        breaker.failure_count = 0
        return await self.repos.circuit_breakers.update(breaker)

    async def record_failure(self, tenant_id: str, service_id: str) -> CircuitBreakerModel:
        breaker = await self.get_or_create(tenant_id, service_id)
        if breaker.state == CircuitBreakerState.HALF_OPEN.value:
            entity = circuit_breaker_to_domain(breaker)
            entity.trip()
            apply_circuit_breaker_domain_to_model(entity, breaker)
            return await self.repos.circuit_breakers.update(breaker)

        breaker.failure_count += 1
        if breaker.failure_count >= breaker.failure_threshold and breaker.state == CircuitBreakerState.CLOSED.value:
            entity = circuit_breaker_to_domain(breaker)
            entity.trip()
            apply_circuit_breaker_domain_to_model(entity, breaker)
        return await self.repos.circuit_breakers.update(breaker)
