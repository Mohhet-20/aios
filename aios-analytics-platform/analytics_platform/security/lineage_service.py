"""Data lineage: source -> transform -> aggregate -> output edges,
plus real multi-hop traversal (not just one-hop lookups) so any number
on a dashboard can be traced all the way back to the raw events that
produced it. Traversal is breadth-first with a depth cap and a
visited-edge set -- lineage graphs can legitimately have diamonds
(two paths converging on the same output), so revisiting a node is
expected; revisiting the same *edge* would just be a cycle or a
duplicate write, and both are worth cutting off rather than looping."""
from __future__ import annotations

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.domain.enums import DataLineageStageType
from analytics_platform.models.security import DataLineageEdgeModel
from analytics_platform.repositories.registry import RepositoryRegistry

DEFAULT_MAX_TRAVERSAL_DEPTH = 10


class DataLineageService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_stage(self, stage_type: str) -> None:
        if stage_type not in {s.value for s in DataLineageStageType}:
            raise ValidationError(f"'{stage_type}' is not a recognized data lineage stage type")

    async def record_edge(
        self, tenant_id: str, *, source_ref: str, target_ref: str, stage_type: str = "transform", transform_description: str | None = None,
    ) -> DataLineageEdgeModel:
        self._assert_valid_stage(stage_type)
        edge = DataLineageEdgeModel(
            tenant_id=tenant_id, source_ref=source_ref, target_ref=target_ref,
            stage_type=stage_type, transform_description=transform_description,
        )
        return await self.repos.data_lineage_edges.add(edge)

    async def _trace(self, tenant_id: str, start_ref: str, *, direction: str, max_depth: int) -> list[dict]:
        fetch = self.repos.data_lineage_edges.list_upstream if direction == "upstream" else self.repos.data_lineage_edges.list_downstream
        visited_edges: set[tuple[str, str]] = set()
        chain: list[dict] = []
        frontier = [start_ref]
        depth = 0
        while frontier and depth < max_depth:
            next_frontier: list[str] = []
            for ref in frontier:
                edges = await fetch(tenant_id, ref)
                for edge in edges:
                    key = (edge.source_ref, edge.target_ref)
                    if key in visited_edges:
                        continue
                    visited_edges.add(key)
                    chain.append({
                        "source_ref": edge.source_ref, "target_ref": edge.target_ref,
                        "stage_type": edge.stage_type, "depth": depth + 1,
                    })
                    next_frontier.append(edge.source_ref if direction == "upstream" else edge.target_ref)
            frontier = next_frontier
            depth += 1
        return chain

    async def trace_upstream(self, tenant_id: str, target_ref: str, *, max_depth: int = DEFAULT_MAX_TRAVERSAL_DEPTH) -> list[dict]:
        return await self._trace(tenant_id, target_ref, direction="upstream", max_depth=max_depth)

    async def trace_downstream(self, tenant_id: str, source_ref: str, *, max_depth: int = DEFAULT_MAX_TRAVERSAL_DEPTH) -> list[dict]:
        return await self._trace(tenant_id, source_ref, direction="downstream", max_depth=max_depth)
