"""Tests for the Inference Platform: service lifecycle transitions,
scaling gated on availability, and weighted route traffic splitting."""
from __future__ import annotations

import pytest

from infra_platform.core.exceptions import InferenceError, InferenceServiceUnavailableError, NotFoundError
from infra_platform.inference.inference_service import InferenceRouteService, InferenceServiceService

TENANT = "tenant-inference"


@pytest.mark.asyncio
async def test_service_lifecycle(repos):
    service = InferenceServiceService(repos)
    inf = await service.deploy_service(TENANT, name="fraud-scorer", mode="real_time", compute_type="gpu")
    assert inf.status == "provisioning"

    inf = await service.mark_running(TENANT, inf.id)
    assert inf.status == "running"

    inf = await service.mark_degraded(TENANT, inf.id)
    assert inf.status == "degraded"

    inf = await service.mark_running(TENANT, inf.id)
    assert inf.status == "running"

    inf = await service.stop(TENANT, inf.id)
    assert inf.status == "stopped"

    inf = await service.terminate(TENANT, inf.id)
    assert inf.status == "terminated"

    with pytest.raises(InferenceError):
        await service.mark_running(TENANT, inf.id)


@pytest.mark.asyncio
async def test_scale_requires_available_service(repos):
    service = InferenceServiceService(repos)
    inf = await service.deploy_service(TENANT, name="batch-scorer", mode="batch")

    with pytest.raises(InferenceServiceUnavailableError):
        await service.scale(TENANT, inf.id, replicas=5)

    inf = await service.mark_running(TENANT, inf.id)
    inf = await service.scale(TENANT, inf.id, replicas=5)
    assert inf.replicas == 5

    with pytest.raises(InferenceError):
        await service.scale(TENANT, inf.id, replicas=-1)


@pytest.mark.asyncio
async def test_route_weighted_traffic_split(repos):
    inf_service = InferenceServiceService(repos)
    route_service = InferenceRouteService(repos)
    inf = await inf_service.deploy_service(TENANT, name="rec-service")

    stable = await route_service.add_route(TENANT, inf.id, path="/v1/stable", weight=90)
    canary = await route_service.add_route(TENANT, inf.id, path="/v1/canary", weight=10)

    routes = await route_service.list_for_service(TENANT, inf.id)
    assert {r.path for r in routes} == {"/v1/stable", "/v1/canary"}

    await route_service.set_weights(TENANT, inf.id, weights={stable.id: 50, canary.id: 50})
    updated = await route_service.list_for_service(TENANT, inf.id)
    assert {r.weight for r in updated} == {50}


@pytest.mark.asyncio
async def test_set_weights_must_sum_to_100(repos):
    inf_service = InferenceServiceService(repos)
    route_service = InferenceRouteService(repos)
    inf = await inf_service.deploy_service(TENANT, name="weights-service")
    r1 = await route_service.add_route(TENANT, inf.id, path="/v1/a", weight=100)

    with pytest.raises(InferenceError):
        await route_service.set_weights(TENANT, inf.id, weights={r1.id: 70})


@pytest.mark.asyncio
async def test_deactivate_and_activate_route(repos):
    inf_service = InferenceServiceService(repos)
    route_service = InferenceRouteService(repos)
    inf = await inf_service.deploy_service(TENANT, name="toggle-service")
    route = await route_service.add_route(TENANT, inf.id, path="/v1/only")

    route = await route_service.deactivate_route(TENANT, route.id)
    assert route.is_active is False
    active = await route_service.list_active_for_service(TENANT, inf.id)
    assert active == []

    route = await route_service.activate_route(TENANT, route.id)
    assert route.is_active is True


@pytest.mark.asyncio
async def test_add_route_unknown_service_raises(repos):
    route_service = InferenceRouteService(repos)
    with pytest.raises(NotFoundError):
        await route_service.add_route(TENANT, "no-such-service", path="/v1/x")
