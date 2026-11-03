"""Service dependency graph derived from real span parent-child edges
that cross a service boundary — the tracing-native counterpart to
`topology/`'s manually-registered dependency graph. Two services with
many trace-derived edges between them are a much stronger "this
actually depends on that" signal than a manually maintained diagram
that drifts out of date."""
from __future__ import annotations

from collections import defaultdict

from observability_platform.repositories.registry import RepositoryRegistry


class TraceDependencyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def service_dependencies_from_trace(self, tenant_id: str, trace_id: str) -> list[dict]:
        spans = await self.repos.spans.list_for_trace(tenant_id, trace_id)
        by_id = {s.span_id: s for s in spans}
        edge_counts: dict[tuple[str, str], int] = defaultdict(int)
        for span in spans:
            if span.parent_span_id is None:
                continue
            parent = by_id.get(span.parent_span_id)
            if parent is None or parent.service_name == span.service_name:
                continue
            edge_counts[(parent.service_name, span.service_name)] += 1
        return [
            {"from_service": src, "to_service": dst, "call_count": count}
            for (src, dst), count in sorted(edge_counts.items())
        ]

    async def service_dependencies_from_recent_traces(self, tenant_id: str, *, limit: int = 100) -> list[dict]:
        """Aggregates dependency edges across the most recent N traces
        rather than just one — the practical "what does this service
        actually call in production" view."""
        traces = await self.repos.traces.list_recent(tenant_id, limit=limit)
        merged: dict[tuple[str, str], int] = defaultdict(int)
        for trace in traces:
            edges = await self.service_dependencies_from_trace(tenant_id, trace.trace_id)
            for edge in edges:
                merged[(edge["from_service"], edge["to_service"])] += edge["call_count"]
        return [
            {"from_service": src, "to_service": dst, "call_count": count}
            for (src, dst), count in sorted(merged.items())
        ]
