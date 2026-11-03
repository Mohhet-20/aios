"""Dependency topology: one edge row per (from_service, to_service)
pair, get-or-create on first call and running-average latency update
on every subsequent one -- the raw material a topology/dependency-graph
view renders, kept as a live rolling aggregate rather than replayed
from raw call logs on every read."""
from __future__ import annotations

from gateway_platform.models.observability import DependencyEdgeModel
from gateway_platform.repositories.registry import RepositoryRegistry


class DependencyTopologyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_call(
        self, tenant_id: str, *, from_service: str, to_service: str, latency_ms: float,
    ) -> DependencyEdgeModel:
        edge = await self.repos.dependency_edges.get_edge(tenant_id, from_service, to_service)
        if edge is None:
            edge = DependencyEdgeModel(
                tenant_id=tenant_id, from_service=from_service, to_service=to_service,
                call_count=1, avg_latency_ms=latency_ms,
            )
            return await self.repos.dependency_edges.add(edge)

        new_count = edge.call_count + 1
        edge.avg_latency_ms = ((edge.avg_latency_ms * edge.call_count) + latency_ms) / new_count
        edge.call_count = new_count
        return await self.repos.dependency_edges.update(edge)

    async def graph(self, tenant_id: str) -> list[DependencyEdgeModel]:
        return await self.repos.dependency_edges.list_for_tenant(tenant_id)

    async def dependencies_of(self, tenant_id: str, service: str) -> list[DependencyEdgeModel]:
        """Services `service` calls (outgoing edges)."""
        return [edge for edge in await self.graph(tenant_id) if edge.from_service == service]

    async def dependents_of(self, tenant_id: str, service: str) -> list[DependencyEdgeModel]:
        """Services that call `service` (incoming edges)."""
        return [edge for edge in await self.graph(tenant_id) if edge.to_service == service]
