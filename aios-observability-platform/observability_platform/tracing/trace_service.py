"""Trace summary lifecycle: get-or-create the denormalized
`TraceModel` row a trace's spans hang off of, finalize it (recompute
span_count/duration/status/started_at/ended_at from the real spans —
never trust a caller-supplied summary), reconstruct the parent-child
span tree for visualization, and check referential integrity."""
from __future__ import annotations

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import OrphanSpanError, TraceTooLargeError
from observability_platform.models.tracing import TraceModel
from observability_platform.repositories.registry import RepositoryRegistry


class TraceService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def get_or_create_trace(
        self, tenant_id: str, trace_id: str, *, root_service: str | None = None, root_operation: str | None = None
    ) -> TraceModel:
        existing = await self.repos.traces.get_by_trace_id(tenant_id, trace_id)
        if existing is not None:
            return existing
        return await self.repos.traces.add(
            TraceModel(tenant_id=tenant_id, trace_id=trace_id, root_service=root_service, root_operation=root_operation)
        )

    async def finalize_trace(self, tenant_id: str, trace_id: str) -> TraceModel:
        """Recomputes the trace summary from its real spans — the same
        anti-drift discipline every prior AIOS platform's derived-metric
        fields follow. Never trusts a caller to report span_count or
        duration directly."""
        spans = await self.repos.spans.list_for_trace(tenant_id, trace_id)
        if len(spans) > self.settings.trace_max_spans_per_trace:
            raise TraceTooLargeError(
                f"Trace '{trace_id}' has {len(spans)} spans, exceeding the limit of "
                f"{self.settings.trace_max_spans_per_trace}"
            )
        trace = await self.get_or_create_trace(tenant_id, trace_id)
        if not spans:
            return trace

        root_spans = [s for s in spans if s.parent_span_id is None]
        if root_spans:
            trace.root_service = root_spans[0].service_name
            trace.root_operation = root_spans[0].operation_name

        trace.span_count = len(spans)
        trace.started_at = min(s.start_time for s in spans)
        ended = [s.end_time for s in spans if s.end_time is not None]
        trace.ended_at = max(ended) if ended else trace.started_at
        trace.duration_ms = (trace.ended_at - trace.started_at).total_seconds() * 1000
        trace.status = "error" if any(s.status == "error" for s in spans) else "ok"
        return await self.repos.traces.update(trace)

    async def check_integrity(self, tenant_id: str, trace_id: str) -> list[str]:
        """Returns the list of span_ids whose parent_span_id doesn't
        resolve to any span in the same trace — orphans, most commonly
        caused by a parent span that was dropped or never flushed. Does
        NOT raise by default (a trace mid-flight legitimately has
        orphans until every service finishes flushing); call
        `raise_on_orphans` for the strict version."""
        spans = await self.repos.spans.list_for_trace(tenant_id, trace_id)
        span_ids = {s.span_id for s in spans}
        return [s.span_id for s in spans if s.parent_span_id is not None and s.parent_span_id not in span_ids]

    async def raise_on_orphans(self, tenant_id: str, trace_id: str) -> None:
        orphans = await self.check_integrity(tenant_id, trace_id)
        if orphans:
            raise OrphanSpanError(f"Trace '{trace_id}' has orphan spans: {orphans}")

    async def build_span_tree(self, tenant_id: str, trace_id: str) -> list[dict]:
        """Reconstructs the parent-child span tree for trace
        visualization. Orphan spans (parent not found) are treated as
        additional roots rather than dropped, so nothing silently
        disappears from the visualization."""
        spans = await self.repos.spans.list_for_trace(tenant_id, trace_id)
        by_id = {s.span_id: s for s in spans}
        children: dict[str | None, list] = {}
        for s in spans:
            parent_key = s.parent_span_id if s.parent_span_id in by_id else None
            children.setdefault(parent_key, []).append(s)

        def _node(span) -> dict:
            return {
                "span_id": span.span_id,
                "service_name": span.service_name,
                "operation_name": span.operation_name,
                "span_kind": span.span_kind,
                "status": span.status,
                "duration_ms": span.duration_ms,
                "children": [_node(c) for c in children.get(span.span_id, [])],
            }

        return [_node(s) for s in children.get(None, [])]
