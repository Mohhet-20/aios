"""ObservabilityService: answers "what happened on this one tool call /
across this one tool's history" from genuinely-recorded data — the
`ToolExecutionModel` timing/status/sandbox_usage columns the Execution
Engine populates as it runs (`tool_execution/engine.py`), and the
structured `ExecutionLogModel` rows it writes via `_log`. This is
Observability, not Analytics: per-execution and per-tool introspection
an Execution Console / Monitoring Dashboard frontend surface needs, not
a cross-workspace BI rollup layer — that's explicitly out of scope per
the tool platform scope boundary.

Honesty principle carried over from the sandbox and execution engine
modules: CPU seconds, peak memory, and network bytes are reported only
when `sandbox_usage` (or, for network, an httpx-backed connector) has
actually recorded them — a tool call that never touched the sandbox
(e.g. `echo`, `database_query`) simply contributes nothing to those
aggregates rather than a fabricated zero-that-looks-like-a-measurement.
Likewise dollar cost is not reported here: nothing in this platform
prices a tool call, so a "cost" field would necessarily be invented.
`get_usage_trends` buckets real `created_at` timestamps by day, which
is as close to "trend" as genuinely-logged data supports without a
separate time-series store."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from tool_platform.repositories.registry import RepositoryRegistry


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _duration_ms(started, completed) -> float | None:
    started, completed = _aware(started), _aware(completed)
    if started is None or completed is None:
        return None
    return (completed - started).total_seconds() * 1000


_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "timed_out", "rolled_back"}


class ObservabilityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- single-execution views ----------------------------------------------------

    async def get_execution_timeline(self, execution_id: str) -> list[dict]:
        """Chronologically merged lifecycle transitions + log lines for one
        tool call — what an Execution Console's detail view renders."""
        execution = await self.repos.executions.get_or_404(execution_id)
        logs = await self.repos.execution_logs.list_for_execution(execution_id)

        events: list[dict] = []
        if execution.created_at:
            events.append({"timestamp": execution.created_at, "type": "created", "attempt": execution.attempt_number})
        if execution.started_at:
            events.append({"timestamp": execution.started_at, "type": "started", "attempt": execution.attempt_number})
        if execution.completed_at:
            events.append({
                "timestamp": execution.completed_at, "type": execution.status,
                "attempt": execution.attempt_number, "duration_ms": execution.duration_ms,
            })
        for log in logs:
            events.append({"timestamp": log.created_at, "type": "log", "level": log.level, "message": log.message})

        events.sort(key=lambda e: _aware(e["timestamp"]))
        for e in events:
            e["timestamp"] = _aware(e["timestamp"]).isoformat()
        return events

    async def list_execution_logs(self, execution_id: str, *, level: str | None = None) -> list:
        return await self.repos.execution_logs.list_for_execution(execution_id, level=level)

    async def get_queue_time_ms(self, execution_id: str) -> float | None:
        execution = await self.repos.executions.get_or_404(execution_id)
        return _duration_ms(execution.created_at, execution.started_at)

    async def get_resource_usage(self, execution_id: str) -> dict:
        """Returns exactly the sandbox's own measured `sandbox_usage` dict
        (cpu_seconds/peak_memory_mb/disk_mb/network_bytes) — empty if this
        execution's connector never ran inside the sandbox, rather than
        backfilling zeros that would look like a real measurement."""
        execution = await self.repos.executions.get_or_404(execution_id)
        return dict(execution.sandbox_usage or {})

    # -- per-tool rollups ("this tool's own history," not cross-tool BI) --------------

    async def get_success_rate(self, tool_id: str) -> dict:
        executions = await self.repos.executions.list_for_tool(tool_id, limit=10_000)
        terminal = [e for e in executions if e.status in _TERMINAL_STATUSES]
        succeeded = [e for e in terminal if e.status == "succeeded"]
        rate = (len(succeeded) / len(terminal)) if terminal else None
        return {
            "tool_id": tool_id, "total_executions": len(executions),
            "terminal_executions": len(terminal), "succeeded": len(succeeded), "success_rate": rate,
        }

    async def get_latency_stats(self, tool_id: str) -> dict:
        executions = await self.repos.executions.list_for_tool(tool_id, limit=10_000)
        durations = sorted(d for d in (e.duration_ms for e in executions) if d is not None)
        if not durations:
            return {"tool_id": tool_id, "sample_size": 0, "avg_ms": None, "min_ms": None, "max_ms": None, "p50_ms": None, "p95_ms": None}
        return {
            "tool_id": tool_id, "sample_size": len(durations),
            "avg_ms": sum(durations) / len(durations), "min_ms": durations[0], "max_ms": durations[-1],
            "p50_ms": durations[len(durations) // 2],
            "p95_ms": durations[min(int(len(durations) * 0.95), len(durations) - 1)],
        }

    async def get_failure_stats(self, tool_id: str, *, sample_limit: int = 5) -> dict:
        executions = await self.repos.executions.list_for_tool(tool_id, limit=10_000)
        failures = [e for e in executions if e.status in ("failed", "timed_out")]
        samples = [e.error_message for e in failures if e.error_message][:sample_limit]
        return {"tool_id": tool_id, "failure_count": len(failures), "sample_errors": samples}

    async def get_retry_stats(self, tool_id: str) -> dict:
        """Count of executions that required at least one retry
        (attempt_number > 1) — a real flakiness signal, not synthesized."""
        executions = await self.repos.executions.list_for_tool(tool_id, limit=10_000)
        retried = [e for e in executions if e.attempt_number > 1]
        return {"tool_id": tool_id, "retried_count": len(retried), "total_executions": len(executions)}

    async def get_resource_usage_stats(self, tool_id: str) -> dict:
        """Aggregates only over executions whose `sandbox_usage` actually
        recorded a given field — sample_size differs per field on
        purpose, since not every connector touches CPU/memory/network."""
        executions = await self.repos.executions.list_for_tool(tool_id, limit=10_000)
        stats: dict[str, dict] = {}
        for field in ("cpu_seconds", "peak_memory_mb", "disk_mb", "network_bytes"):
            values = [e.sandbox_usage[field] for e in executions if e.sandbox_usage and field in e.sandbox_usage]
            if values:
                stats[field] = {"sample_size": len(values), "avg": sum(values) / len(values), "max": max(values)}
            else:
                stats[field] = {"sample_size": 0, "avg": None, "max": None}
        return stats

    async def get_usage_trends(self, tool_id: str, *, bucket: str = "day") -> dict[str, int]:
        """Real call-volume-over-time, bucketed by UTC calendar day (the
        only granularity genuinely-logged `created_at` timestamps support
        without a dedicated time-series store)."""
        executions = await self.repos.executions.list_for_tool(tool_id, limit=10_000)
        buckets: dict[str, int] = defaultdict(int)
        for execution in executions:
            created = _aware(execution.created_at)
            if created is None:
                continue
            key = created.date().isoformat()
            buckets[key] += 1
        return dict(sorted(buckets.items()))

    # -- workspace-wide (still "this workspace's own history") -------------------------

    async def get_workspace_call_volume(self, workspace_id: str) -> dict:
        executions = await self.repos.executions.list_for_workspace(workspace_id, limit=10_000)
        by_status: dict[str, int] = defaultdict(int)
        for execution in executions:
            by_status[execution.status] += 1
        return {"workspace_id": workspace_id, "total_calls": len(executions), "by_status": dict(by_status)}
