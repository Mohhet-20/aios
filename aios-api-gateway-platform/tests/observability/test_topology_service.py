from __future__ import annotations

import pytest

from gateway_platform.observability.topology_service import DependencyTopologyService

TENANT = "obs-topo-tenant"


@pytest.mark.asyncio
async def test_record_call_creates_edge(repos):
    service = DependencyTopologyService(repos)
    edge = await service.record_call(TENANT, from_service="gateway", to_service="orders", latency_ms=100.0)
    assert edge.call_count == 1
    assert edge.avg_latency_ms == 100.0


@pytest.mark.asyncio
async def test_record_call_updates_running_average(repos):
    service = DependencyTopologyService(repos)
    await service.record_call(TENANT, from_service="gateway", to_service="inventory", latency_ms=100.0)
    edge = await service.record_call(TENANT, from_service="gateway", to_service="inventory", latency_ms=200.0)
    assert edge.call_count == 2
    assert edge.avg_latency_ms == 150.0


@pytest.mark.asyncio
async def test_graph_and_dependencies_and_dependents(repos):
    service = DependencyTopologyService(repos)
    await service.record_call(TENANT, from_service="gateway", to_service="billing", latency_ms=50.0)
    await service.record_call(TENANT, from_service="billing", to_service="ledger", latency_ms=30.0)

    graph = await service.graph(TENANT)
    assert len(graph) == 2

    deps = await service.dependencies_of(TENANT, "gateway")
    assert {e.to_service for e in deps} == {"billing"}

    dependents = await service.dependents_of(TENANT, "ledger")
    assert {e.from_service for e in dependents} == {"billing"}
