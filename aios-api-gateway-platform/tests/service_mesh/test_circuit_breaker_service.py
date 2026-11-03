from __future__ import annotations

import pytest

from gateway_platform.config.settings import Settings
from gateway_platform.core.exceptions import CircuitBreakerOpenError
from gateway_platform.service_mesh.circuit_breaker_service import CircuitBreakerService

TENANT = "cb-tenant"


@pytest.mark.asyncio
async def test_trips_after_threshold_failures(repos):
    settings = Settings(mesh_circuit_breaker_failure_threshold=3)
    service = CircuitBreakerService(repos, settings=settings)
    for _ in range(2):
        breaker = await service.record_failure(TENANT, "svc-a")
        assert breaker.state == "closed"
    breaker = await service.record_failure(TENANT, "svc-a")
    assert breaker.state == "open"


@pytest.mark.asyncio
async def test_enforce_raises_while_open(repos):
    settings = Settings(mesh_circuit_breaker_failure_threshold=1, mesh_circuit_breaker_open_seconds=3600)
    service = CircuitBreakerService(repos, settings=settings)
    await service.record_failure(TENANT, "svc-b")
    with pytest.raises(CircuitBreakerOpenError):
        await service.enforce(TENANT, "svc-b")


@pytest.mark.asyncio
async def test_moves_to_half_open_after_timeout_elapses(repos):
    settings = Settings(mesh_circuit_breaker_failure_threshold=1, mesh_circuit_breaker_open_seconds=0)
    service = CircuitBreakerService(repos, settings=settings)
    await service.record_failure(TENANT, "svc-c")
    breaker = await service.enforce(TENANT, "svc-c")
    assert breaker.state == "half_open"


@pytest.mark.asyncio
async def test_success_in_half_open_closes_breaker(repos):
    settings = Settings(mesh_circuit_breaker_failure_threshold=1, mesh_circuit_breaker_open_seconds=0)
    service = CircuitBreakerService(repos, settings=settings)
    await service.record_failure(TENANT, "svc-d")
    await service.enforce(TENANT, "svc-d")  # transitions to half_open
    closed = await service.record_success(TENANT, "svc-d")
    assert closed.state == "closed"
    assert closed.failure_count == 0


@pytest.mark.asyncio
async def test_failure_in_half_open_reopens_breaker(repos):
    settings = Settings(mesh_circuit_breaker_failure_threshold=1, mesh_circuit_breaker_open_seconds=0)
    service = CircuitBreakerService(repos, settings=settings)
    await service.record_failure(TENANT, "svc-e")
    await service.enforce(TENANT, "svc-e")  # transitions to half_open
    reopened = await service.record_failure(TENANT, "svc-e")
    assert reopened.state == "open"
