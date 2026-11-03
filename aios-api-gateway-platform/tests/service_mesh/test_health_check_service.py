from __future__ import annotations

import pytest

from gateway_platform.config.settings import Settings
from gateway_platform.service_mesh.health_check_service import HealthCheckService
from gateway_platform.service_mesh.registry_service import ServiceRegistryService

TENANT = "hc-tenant"


@pytest.mark.asyncio
async def test_healthy_results_keep_instance_active(repos):
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="hc-svc-1")
    instance = await registry.register_instance(TENANT, svc.id, host="a")

    hc = HealthCheckService(repos)
    await hc.record_result(TENANT, instance.id, healthy=True, latency_ms=12.0)
    refreshed = await repos.service_instances.get(instance.id)
    assert refreshed.status == "active"


@pytest.mark.asyncio
async def test_consecutive_failures_mark_instance_unhealthy(repos):
    settings = Settings(mesh_health_check_failure_threshold=2)
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="hc-svc-2")
    instance = await registry.register_instance(TENANT, svc.id, host="b")

    hc = HealthCheckService(repos, settings=settings)
    await hc.record_result(TENANT, instance.id, healthy=False)
    still_active = await repos.service_instances.get(instance.id)
    assert still_active.status == "active"

    await hc.record_result(TENANT, instance.id, healthy=False)
    now_unhealthy = await repos.service_instances.get(instance.id)
    assert now_unhealthy.status == "unhealthy"


@pytest.mark.asyncio
async def test_automatic_recovery_on_healthy_result(repos):
    settings = Settings(mesh_health_check_failure_threshold=1)
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="hc-svc-3")
    instance = await registry.register_instance(TENANT, svc.id, host="c")

    hc = HealthCheckService(repos, settings=settings)
    await hc.record_result(TENANT, instance.id, healthy=False)
    unhealthy = await repos.service_instances.get(instance.id)
    assert unhealthy.status == "unhealthy"

    await hc.record_result(TENANT, instance.id, healthy=True)
    recovered = await repos.service_instances.get(instance.id)
    assert recovered.status == "active"


@pytest.mark.asyncio
async def test_list_for_instance_returns_recent_results(repos):
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="hc-svc-4")
    instance = await registry.register_instance(TENANT, svc.id, host="d")
    hc = HealthCheckService(repos)
    await hc.record_result(TENANT, instance.id, healthy=True)
    await hc.record_result(TENANT, instance.id, healthy=True)
    results = await hc.list_for_instance(TENANT, instance.id)
    assert len(results) == 2
