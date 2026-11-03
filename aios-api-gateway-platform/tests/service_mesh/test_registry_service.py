from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import InvalidTransitionError
from gateway_platform.domain.enums import InstanceStatus
from gateway_platform.service_mesh.registry_service import ServiceRegistryService

TENANT = "mesh-tenant"


@pytest.mark.asyncio
async def test_register_service_is_idempotent_by_name(repos):
    service = ServiceRegistryService(repos)
    a = await service.register_service(TENANT, name="orders-svc")
    b = await service.register_service(TENANT, name="orders-svc")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_service_status_lifecycle(repos):
    service = ServiceRegistryService(repos)
    svc = await service.register_service(TENANT, name="inventory-svc")
    healthy = await service.mark_healthy(TENANT, svc.id)
    assert healthy.status == "healthy"
    unhealthy = await service.mark_unhealthy(TENANT, svc.id)
    assert unhealthy.status == "unhealthy"
    deregistered = await service.deregister_service(TENANT, svc.id)
    assert deregistered.status == "deregistered"
    with pytest.raises(InvalidTransitionError):
        await service.mark_healthy(TENANT, svc.id)


@pytest.mark.asyncio
async def test_register_and_list_instances(repos):
    service = ServiceRegistryService(repos)
    svc = await service.register_service(TENANT, name="billing-svc")
    i1 = await service.register_instance(TENANT, svc.id, host="10.0.0.1", port=8080)
    await service.register_instance(TENANT, svc.id, host="10.0.0.2", port=8080)
    instances = await service.list_instances(TENANT, svc.id)
    assert len(instances) == 2
    assert i1.status == "active"


@pytest.mark.asyncio
async def test_instance_transitions(repos):
    service = ServiceRegistryService(repos)
    svc = await service.register_service(TENANT, name="notify-svc")
    instance = await service.register_instance(TENANT, svc.id, host="10.0.0.3")
    draining = await service.transition_instance(TENANT, instance.id, InstanceStatus.DRAINING)
    assert draining.status == "draining"
    removed = await service.transition_instance(TENANT, instance.id, InstanceStatus.REMOVED)
    assert removed.status == "removed"
    with pytest.raises(InvalidTransitionError):
        await service.transition_instance(TENANT, instance.id, InstanceStatus.ACTIVE)
