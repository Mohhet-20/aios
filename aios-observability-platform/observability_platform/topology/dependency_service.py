"""Failure-propagation analysis over the registered topology graph. An
edge `source -> target` means "source depends on target," so if
`target` fails, the blast radius is everything with a (possibly
transitive) path INTO it — walked here via BFS over incoming edges."""
from __future__ import annotations

from observability_platform.repositories.registry import RepositoryRegistry


class TopologyDependencyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def downstream_impact(self, tenant_id: str, node_id: str) -> list[str]:
        """Every node that would be impacted, directly or transitively,
        if `node_id` fails."""
        visited = {node_id}
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            incoming = await self.repos.topology_edges.list_incoming(tenant_id, current)
            for edge in incoming:
                if edge.source_node_id not in visited:
                    visited.add(edge.source_node_id)
                    queue.append(edge.source_node_id)
        visited.discard(node_id)
        return sorted(visited)

    async def upstream_dependencies(self, tenant_id: str, node_id: str) -> list[str]:
        """Everything `node_id` itself (transitively) depends on — what
        needs to be healthy for `node_id` to function."""
        visited = {node_id}
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            outgoing = await self.repos.topology_edges.list_outgoing(tenant_id, current)
            for edge in outgoing:
                if edge.target_node_id not in visited:
                    visited.add(edge.target_node_id)
                    queue.append(edge.target_node_id)
        visited.discard(node_id)
        return sorted(visited)
