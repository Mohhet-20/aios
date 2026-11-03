"""ORM <-> domain-aggregate bridge for `CircuitBreaker`."""
from __future__ import annotations

from gateway_platform.domain.entities import CircuitBreaker
from gateway_platform.domain.enums import CircuitBreakerState
from gateway_platform.models.mesh import CircuitBreakerModel


def circuit_breaker_to_domain(model: CircuitBreakerModel) -> CircuitBreaker:
    return CircuitBreaker(
        id=model.id, state=CircuitBreakerState(model.state),
        opened_at=model.opened_at, half_opened_at=model.half_opened_at,
    )


def apply_circuit_breaker_domain_to_model(entity: CircuitBreaker, model: CircuitBreakerModel) -> None:
    model.state = entity.state.value
    model.opened_at = entity.opened_at
    model.half_opened_at = entity.half_opened_at
