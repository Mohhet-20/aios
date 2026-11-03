"""Performance analysis: latency analysis and bottleneck/slow-query
detection built entirely on top of the metrics and tracing modules —
this service adds no new tables of its own, it's a read-side
aggregation layer, the same "compute on demand from real data, never
cache" discipline every prior AIOS platform's observability layer uses.

Capacity trend analysis intentionally lives in `capacity/
forecast_service.py`, not here — this service answers "why is it slow
right now / what's the bottleneck," capacity planning answers "when
will we run out," and conflating the two would blur two genuinely
different operational questions into one god-service."""
from __future__ import annotations

from datetime import datetime

from observability_platform.core.exceptions import PerformanceAnalysisError
from observability_platform.metrics.aggregation_service import AggregationResult, aggregate
from observability_platform.metrics.query_service import MetricQueryService
from observability_platform.repositories.registry import RepositoryRegistry


class PerformanceAnalysisService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.metric_query = MetricQueryService(repos)

    async def latency_analysis(
        self, tenant_id: str, metric_name: str, *, component_id: str | None = None,
        start_time: datetime | None = None, end_time: datetime | None = None,
    ) -> AggregationResult:
        return await self.metric_query.aggregate_range(
            tenant_id, metric_name, component_id=component_id, start_time=start_time, end_time=end_time
        )

    async def detect_bottleneck(self, tenant_id: str, trace_id: str) -> dict:
        """Finds the span responsible for the largest share of a trace's
        total wall-clock duration, ranked by *self time*
        (`duration_ms` minus the summed duration of its direct
        children) rather than raw `duration_ms`. Raw duration is the
        wrong signal here: a parent span's duration always includes
        every child's duration, so ranking by raw duration would almost
        always crown the root span "the bottleneck" regardless of where
        the actual work happened — self time isolates the span that is
        itself slow, not the span that merely wraps slow children."""
        spans = await self.repos.spans.list_for_trace(tenant_id, trace_id)
        timed_spans = [s for s in spans if s.duration_ms is not None]
        if not timed_spans:
            raise PerformanceAnalysisError(f"Trace '{trace_id}' has no completed spans to analyze")
        trace = await self.repos.traces.get_by_trace_id(tenant_id, trace_id)
        total_ms = trace.duration_ms if trace and trace.duration_ms else max(s.duration_ms for s in timed_spans)

        children_duration: dict[str, float] = {}
        for s in timed_spans:
            if s.parent_span_id:
                children_duration[s.parent_span_id] = children_duration.get(s.parent_span_id, 0.0) + s.duration_ms

        def self_time(span) -> float:
            return span.duration_ms - children_duration.get(span.span_id, 0.0)

        bottleneck = max(timed_spans, key=self_time)
        share_pct = (self_time(bottleneck) / total_ms * 100) if total_ms else 0.0
        return {
            "span_id": bottleneck.span_id,
            "service_name": bottleneck.service_name,
            "operation_name": bottleneck.operation_name,
            "duration_ms": bottleneck.duration_ms,
            "self_time_ms": round(self_time(bottleneck), 3),
            "share_of_trace_pct": round(share_pct, 2),
        }

    async def slow_query_analysis(self, tenant_id: str, *, threshold_ms: float = 100.0, limit: int = 5000) -> list[dict]:
        """Scans recent database_query spans directly (independent of
        whether their parent trace has been finalized) and groups the
        slow ones by operation name — a rough substitute for a real
        database's own slow-query log, built from what this platform
        already observes at the tracing layer."""
        spans = await self.repos.spans.list_recent_for_tenant(tenant_id, span_kind="database_query", limit=limit)
        by_operation: dict[str, list[float]] = {}
        for span in spans:
            if span.duration_ms and span.duration_ms >= threshold_ms:
                by_operation.setdefault(span.operation_name, []).append(span.duration_ms)
        return [
            {"operation_name": op, **aggregate(durations).__dict__}
            for op, durations in sorted(by_operation.items(), key=lambda kv: -max(kv[1]))
        ]

    async def performance_by_span_kind(self, tenant_id: str, span_kind: str, *, limit: int = 5000) -> list[dict]:
        """Groups span durations by operation name for a given
        `span_kind` — pass "workflow_step", "agent_execution", or
        "tool_call" for workflow/agent/tool performance summaries, or
        "server"/"client" for API performance."""
        spans = await self.repos.spans.list_recent_for_tenant(tenant_id, span_kind=span_kind, limit=limit)
        by_operation: dict[str, list[float]] = {}
        for span in spans:
            if span.duration_ms is not None:
                by_operation.setdefault(span.operation_name, []).append(span.duration_ms)
        return [
            {"operation_name": op, **aggregate(durations).__dict__}
            for op, durations in sorted(by_operation.items())
        ]

    async def cache_analysis(self, tenant_id: str, *, metric_name: str = "cache_hit_ratio") -> AggregationResult:
        return await self.metric_query.aggregate_range(tenant_id, metric_name)
