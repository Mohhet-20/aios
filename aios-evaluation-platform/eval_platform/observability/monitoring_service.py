"""ObservabilityMonitoringService: read-side aggregation over ingested
`ObservabilityEventModel` rows — an execution timeline, latency stats
(including a real percentile, not just avg/min/max), failure/retry/
error-type breakdowns, and resource/token/cost totals. Every number
here is derived only from events that actually reported the relevant
field; an empty `resource_usage`/`token_usage`/`cost` on an event
simply doesn't contribute to that aggregate, rather than being treated
as zero."""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timezone

from eval_platform.models.observability import ObservabilityEventModel
from eval_platform.repositories.registry import RepositoryRegistry


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on DateTime round-trip; every timestamp this
    platform writes is UTC (`database.base.utcnow`), so a naive value
    reloaded from the database is safely treated as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ObservabilityMonitoringService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_timeline(self, workspace_id: str, source_execution_id: str) -> list[ObservabilityEventModel]:
        events = await self.repos.observability_events.list_for_workspace(workspace_id, source_execution_id=source_execution_id, limit=1000)
        return sorted(events, key=lambda e: _aware(e.created_at))

    async def get_latency_stats(self, workspace_id: str, *, event_type: str | None = None) -> dict:
        events = await self.repos.observability_events.list_for_workspace(workspace_id, event_type=event_type, limit=5000)
        latencies = sorted(e.latency_ms for e in events if e.latency_ms is not None)
        if not latencies:
            return {"sample_count": 0, "avg_ms": None, "min_ms": None, "max_ms": None, "p95_ms": None}
        p95 = latencies[-1] if len(latencies) == 1 else statistics.quantiles(latencies, n=100)[94]
        return {
            "sample_count": len(latencies), "avg_ms": sum(latencies) / len(latencies),
            "min_ms": latencies[0], "max_ms": latencies[-1], "p95_ms": p95,
        }

    async def get_queue_time_stats(self, workspace_id: str) -> dict:
        events = await self.repos.observability_events.list_for_workspace(workspace_id, limit=5000)
        queue_times = [e.queue_time_ms for e in events if e.queue_time_ms is not None]
        if not queue_times:
            return {"sample_count": 0, "avg_ms": None}
        return {"sample_count": len(queue_times), "avg_ms": sum(queue_times) / len(queue_times)}

    async def get_failure_stats(self, workspace_id: str) -> dict:
        events = await self.repos.observability_events.list_for_workspace(workspace_id, limit=5000)
        total = len(events)
        failed = [e for e in events if e.status == "failed"]
        retried = [e for e in events if e.status == "retried"]
        error_type_counts = Counter(e.error_type for e in failed if e.error_type)
        return {
            "total_events": total, "failure_count": len(failed), "retried_count": len(retried),
            "failure_rate": (len(failed) / total) if total else 0.0,
            "total_retries": sum(e.retry_count for e in events),
            "error_type_breakdown": dict(error_type_counts),
        }

    async def get_resource_usage_stats(self, workspace_id: str) -> dict:
        events = await self.repos.observability_events.list_for_workspace(workspace_id, limit=5000)
        totals: dict[str, float] = {}
        counts: dict[str, int] = {}
        for event in events:
            for key, value in (event.resource_usage or {}).items():
                if value is None:
                    continue
                totals[key] = totals.get(key, 0.0) + value
                counts[key] = counts.get(key, 0) + 1
        return {
            key: {"total": totals[key], "avg": totals[key] / counts[key], "sample_count": counts[key]}
            for key in totals
        }

    async def get_token_and_cost_stats(self, workspace_id: str) -> dict:
        events = await self.repos.observability_events.list_for_workspace(workspace_id, limit=5000)
        input_tokens = sum(e.token_usage.get("input_tokens", 0) for e in events if e.token_usage)
        output_tokens = sum(e.token_usage.get("output_tokens", 0) for e in events if e.token_usage)
        costs = [e.cost for e in events if e.cost is not None]
        return {
            "input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens,
            "total_cost": sum(costs) if costs else None, "cost_sample_count": len(costs),
        }
