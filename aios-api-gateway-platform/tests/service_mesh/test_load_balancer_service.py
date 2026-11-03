from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import NoHealthyInstancesError, ValidationError
from gateway_platform.service_mesh.load_balancer_service import LoadBalancerService
from gateway_platform.service_mesh.registry_service import ServiceRegistryService

TENANT = "lb-tenant"


@pytest.mark.asyncio
async def test_round_robin_cycles_through_instances(repos):
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="rr-svc")
    i1 = await registry.register_instance(TENANT, svc.id, host="a")
    i2 = await registry.register_instance(TENANT, svc.id, host="b")

    lb = LoadBalancerService(repos)
    await lb.configure_pool(TENANT, svc.id, strategy="round_robin")
    picks = [(await lb.select_instance(TENANT, svc.id)).id for _ in range(4)]
    assert picks == [i1.id, i2.id, i1.id, i2.id]


@pytest.mark.asyncio
async def test_weighted_selection_uses_injectable_rand(repos):
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="weighted-svc")
    i1 = await registry.register_instance(TENANT, svc.id, host="a", weight=1)
    i2 = await registry.register_instance(TENANT, svc.id, host="b", weight=9)

    lb = LoadBalancerService(repos, rand=lambda: 0.95)  # lands in i2's weighted slice
    await lb.configure_pool(TENANT, svc.id, strategy="weighted")
    picked = await lb.select_instance(TENANT, svc.id)
    assert picked.id == i2.id

    lb_low = LoadBalancerService(repos, rand=lambda: 0.05)  # lands in i1's slice
    picked_low = await lb_low.select_instance(TENANT, svc.id)
    assert picked_low.id == i1.id


@pytest.mark.asyncio
async def test_no_healthy_instances_raises(repos):
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="empty-svc")
    lb = LoadBalancerService(repos)
    with pytest.raises(NoHealthyInstancesError):
        await lb.select_instance(TENANT, svc.id)


@pytest.mark.asyncio
async def test_invalid_strategy_rejected(repos):
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="bad-strategy-svc")
    lb = LoadBalancerService(repos)
    with pytest.raises(ValidationError):
        await lb.configure_pool(TENANT, svc.id, strategy="coin_flip")


@pytest.mark.asyncio
async def test_default_strategy_used_when_no_pool_configured(repos):
    registry = ServiceRegistryService(repos)
    svc = await registry.register_service(TENANT, name="default-strategy-svc")
    await registry.register_instance(TENANT, svc.id, host="a")
    lb = LoadBalancerService(repos)
    picked = await lb.select_instance(TENANT, svc.id)
    assert picked.host == "a"
