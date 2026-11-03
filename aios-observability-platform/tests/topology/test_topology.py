from __future__ import annotations

import pytest

from observability_platform.core.exceptions import DependencyCycleError
from observability_platform.topology.dependency_service import TopologyDependencyService
from observability_platform.topology.service_map_service import ServiceMapService


async def _build_chain(repos):
    """api -> ai-core -> tool-platform -> external-search
    Also: workflow-engine -> ai-core (a second, independent caller of ai-core)."""
    svc = ServiceMapService(repos)
    api = await svc.register_node("t1", name="api-gateway", node_type="service")
    ai_core = await svc.register_node("t1", name="ai-core", node_type="service")
    tool_platform = await svc.register_node("t1", name="tool-platform", node_type="service")
    external = await svc.register_node("t1", name="external-search", node_type="external_integration")
    workflow = await svc.register_node("t1", name="workflow-engine", node_type="service")

    await svc.add_edge("t1", source_node_id=api.id, target_node_id=ai_core.id, edge_type="service")
    await svc.add_edge("t1", source_node_id=ai_core.id, target_node_id=tool_platform.id, edge_type="service")
    await svc.add_edge("t1", source_node_id=tool_platform.id, target_node_id=external.id, edge_type="external_integration")
    await svc.add_edge("t1", source_node_id=workflow.id, target_node_id=ai_core.id, edge_type="service")
    return {"api": api, "ai_core": ai_core, "tool_platform": tool_platform, "external": external, "workflow": workflow}


@pytest.mark.asyncio
async def test_register_node_and_add_edge(repos):
    svc = ServiceMapService(repos)
    await _build_chain(repos)
    service_map = await svc.get_service_map("t1")
    assert len(service_map["nodes"]) == 5
    assert len(service_map["edges"]) == 4


@pytest.mark.asyncio
async def test_add_edge_rejects_self_dependency(repos):
    svc = ServiceMapService(repos)
    node = await svc.register_node("t1", name="lonely-service", node_type="service")
    with pytest.raises(DependencyCycleError):
        await svc.add_edge("t1", source_node_id=node.id, target_node_id=node.id, edge_type="service")


@pytest.mark.asyncio
async def test_downstream_impact_finds_all_transitive_callers(repos):
    nodes = await _build_chain(repos)
    dep_svc = TopologyDependencyService(repos)

    impact = await dep_svc.downstream_impact("t1", nodes["external"].id)
    impacted_ids = set(impact)
    assert nodes["tool_platform"].id in impacted_ids
    assert nodes["ai_core"].id in impacted_ids
    assert nodes["api"].id in impacted_ids
    assert nodes["workflow"].id in impacted_ids  # transitively, via ai-core
    assert nodes["external"].id not in impacted_ids  # the failing node itself isn't in its own blast radius


@pytest.mark.asyncio
async def test_upstream_dependencies_finds_everything_relied_upon(repos):
    nodes = await _build_chain(repos)
    dep_svc = TopologyDependencyService(repos)

    deps = await dep_svc.upstream_dependencies("t1", nodes["api"].id)
    dep_ids = set(deps)
    assert nodes["ai_core"].id in dep_ids
    assert nodes["tool_platform"].id in dep_ids
    assert nodes["external"].id in dep_ids
    assert nodes["workflow"].id not in dep_ids  # workflow-engine is a sibling caller, not a dependency of api


@pytest.mark.asyncio
async def test_downstream_impact_of_leaf_node_with_no_dependents_is_empty(repos):
    svc = ServiceMapService(repos)
    isolated = await svc.register_node("t1", name="isolated-service", node_type="service")
    dep_svc = TopologyDependencyService(repos)
    impact = await dep_svc.downstream_impact("t1", isolated.id)
    assert impact == []
