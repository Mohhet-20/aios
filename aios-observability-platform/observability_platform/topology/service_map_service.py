"""Service/infrastructure topology registry: nodes are things
(services, workflows, agents, tools, external integrations,
infrastructure) and edges are typed, directed "depends on" relationships
(`source` calls/depends on `target`). Deliberately does NOT enforce the
graph stay acyclic — real microservice topologies legitimately have
circular call patterns (bidirectional sync services, event-driven
mutual triggers), so `DependencyCycleError` is reserved for the one
genuinely nonsensical case: a node declared to depend on itself."""
from __future__ import annotations

from observability_platform.core.exceptions import DependencyCycleError
from observability_platform.models.topology import TopologyEdgeModel, TopologyNodeModel
from observability_platform.repositories.registry import RepositoryRegistry


class ServiceMapService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register_node(
        self, tenant_id: str, *, name: str, node_type: str, component_id: str | None = None, metadata: dict | None = None
    ) -> TopologyNodeModel:
        node = TopologyNodeModel(tenant_id=tenant_id, name=name, node_type=node_type, component_id=component_id, node_metadata=metadata or {})
        return await self.repos.topology_nodes.add(node)

    async def add_edge(
        self, tenant_id: str, *, source_node_id: str, target_node_id: str, edge_type: str, metadata: dict | None = None
    ) -> TopologyEdgeModel:
        if source_node_id == target_node_id:
            raise DependencyCycleError("A topology node cannot depend on itself")
        edge = TopologyEdgeModel(
            tenant_id=tenant_id, source_node_id=source_node_id, target_node_id=target_node_id,
            edge_type=edge_type, edge_metadata=metadata or {},
        )
        return await self.repos.topology_edges.add(edge)

    async def get_service_map(self, tenant_id: str) -> dict:
        nodes = await self.repos.topology_nodes.list_for_tenant(tenant_id)
        edges = await self.repos.topology_edges.list_for_tenant(tenant_id)
        return {
            "nodes": [{"id": n.id, "name": n.name, "node_type": n.node_type, "component_id": n.component_id} for n in nodes],
            "edges": [{"source": e.source_node_id, "target": e.target_node_id, "edge_type": e.edge_type} for e in edges],
        }
