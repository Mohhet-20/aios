"""ObservabilityService: every metric here is computed from genuinely
logged operational data — `NodeExecutionModel`/`ExecutionModel` timing
columns the Execution Engine populates as it runs, and the structured
`ExecutionLogModel` rows it writes at every node success/retry/failure
(see `workflow_engine/engine.py`'s `_log`) — never synthesized numbers.
This is Observability, not Analytics: it answers "what happened on this
one execution / to this one workflow's node types," the per-run and
per-workflow introspection an Execution Timeline, Execution Graph, or
Node Inspector frontend surface needs. A cross-workflow rollup/BI layer
(trends over time, workspace-wide dashboards) is explicitly out of scope
by design — that's the (not-yet-built) Analytics
module.

Two metrics this service does NOT report, on purpose, rather than
faking plausible-looking numbers: CPU/memory resource usage (this
platform has no process-level instrumentation hook to measure it) and
dollar cost (AI Core's `CostCalculator` isn't wired into the Execution
Engine yet — token usage, which *is* real logged data from every
LLM_CALL node's output, is reported instead, with cost as a documented
follow-on once that wiring exists)."""
from __future__ import annotations

from workflow_platform.repositories.registry import RepositoryRegistry


def _duration_ms(started, completed) -> float | None:
    if started is None or completed is None:
        return None
    from datetime import timezone

    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    return (completed - started).total_seconds() * 1000


class ObservabilityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- single-execution views ----------------------------------------------------

    async def get_execution_timeline(self, execution_id: str) -> list[dict]:
        """A chronologically merged view of node lifecycle transitions and
        log lines — what an Execution Timeline frontend surface renders."""
        node_executions = await self.repos.node_executions.list_for_execution(execution_id)
        logs = await self.repos.execution_logs.list_for_execution(execution_id)

        events: list[dict] = []
        for ne in node_executions:
            if ne.started_at:
                events.append({"timestamp": ne.started_at, "type": "node_started", "node_key": ne.node_key, "attempt": ne.attempt_number})
            if ne.completed_at:
                events.append({
                    "timestamp": ne.completed_at, "type": f"node_{ne.status}", "node_key": ne.node_key,
                    "attempt": ne.attempt_number, "duration_ms": ne.duration_ms,
                })
        for log in logs:
            events.append({"timestamp": log.created_at, "type": "log", "level": log.level, "message": log.message, "node_execution_id": log.node_execution_id})

        events.sort(key=lambda e: e["timestamp"])
        for e in events:
            e["timestamp"] = e["timestamp"].isoformat()
        return events

    async def get_execution_graph(self, execution_id: str) -> dict:
        """The graph shape (nodes + edges) for this execution's specific
        pinned `workflow_version_id`, annotated with each node's actual
        outcome — what an Execution Graph frontend surface renders."""
        execution = await self.repos.executions.get_or_404(execution_id)
        nodes = await self.repos.workflow_nodes.list_for_version(execution.workflow_version_id)
        edges = await self.repos.workflow_edges.list_for_version(execution.workflow_version_id)
        node_executions = {ne.node_key: ne for ne in await self.repos.node_executions.list_for_execution(execution_id)}

        return {
            "execution_id": execution_id,
            "nodes": [
                {
                    "node_key": n.node_key, "node_type": n.node_type, "name": n.name,
                    "status": node_executions[n.node_key].status if n.node_key in node_executions else "not_reached",
                    "duration_ms": node_executions[n.node_key].duration_ms if n.node_key in node_executions else None,
                    "attempt_number": node_executions[n.node_key].attempt_number if n.node_key in node_executions else None,
                }
                for n in nodes
            ],
            "edges": [{"source": e.source_node_key, "target": e.target_node_key, "condition": e.condition} for e in edges],
        }

    async def list_execution_logs(self, execution_id: str, *, level: str | None = None) -> list:
        return await self.repos.execution_logs.list_for_execution(execution_id, level=level)

    async def get_queue_time_ms(self, execution_id: str) -> float | None:
        """Time between an execution being created (queued) and actually
        starting to run — distinct from total execution duration."""
        execution = await self.repos.executions.get_or_404(execution_id)
        return _duration_ms(execution.created_at, execution.started_at)

    # -- per-workflow rollups (still "this workflow's own history," not cross-workflow BI) --

    async def get_success_rate(self, workflow_id: str) -> dict:
        executions = await self.repos.executions.list_for_workflow(workflow_id, limit=10_000)
        terminal_statuses = {"completed", "failed", "cancelled", "compensated"}
        terminal = [e for e in executions if e.status in terminal_statuses]
        completed = [e for e in terminal if e.status == "completed"]
        rate = (len(completed) / len(terminal)) if terminal else None
        return {"workflow_id": workflow_id, "total_executions": len(executions), "terminal_executions": len(terminal), "completed": len(completed), "success_rate": rate}

    async def get_latency_stats(self, workflow_id: str) -> dict:
        executions = await self.repos.executions.list_for_workflow(workflow_id, limit=10_000)
        durations = sorted(d for d in (_duration_ms(e.started_at, e.completed_at) for e in executions) if d is not None)
        if not durations:
            return {"workflow_id": workflow_id, "sample_size": 0, "avg_ms": None, "min_ms": None, "max_ms": None, "p50_ms": None, "p95_ms": None}
        return {
            "workflow_id": workflow_id, "sample_size": len(durations),
            "avg_ms": sum(durations) / len(durations), "min_ms": durations[0], "max_ms": durations[-1],
            "p50_ms": durations[len(durations) // 2], "p95_ms": durations[int(len(durations) * 0.95) if len(durations) > 1 else 0],
        }

    async def get_node_duration_stats(self, workflow_id: str) -> dict[str, dict]:
        """Per-`node_key` duration stats across every execution of this
        workflow — which node types are the slow ones."""
        executions = await self.repos.executions.list_for_workflow(workflow_id, limit=10_000)
        by_node: dict[str, list[float]] = {}
        for execution in executions:
            for ne in await self.repos.node_executions.list_for_execution(execution.id):
                if ne.duration_ms is not None:
                    by_node.setdefault(ne.node_key, []).append(ne.duration_ms)
        return {
            node_key: {"sample_size": len(durations), "avg_ms": sum(durations) / len(durations), "min_ms": min(durations), "max_ms": max(durations)}
            for node_key, durations in by_node.items()
        }

    async def get_failure_stats(self, workflow_id: str) -> dict[str, dict]:
        executions = await self.repos.executions.list_for_workflow(workflow_id, limit=10_000)
        by_node: dict[str, dict] = {}
        for execution in executions:
            for ne in await self.repos.node_executions.list_for_execution(execution.id):
                if ne.status != "failed":
                    continue
                entry = by_node.setdefault(ne.node_key, {"failure_count": 0, "sample_errors": []})
                entry["failure_count"] += 1
                if ne.error_message and len(entry["sample_errors"]) < 5:
                    entry["sample_errors"].append(ne.error_message)
        return by_node

    async def get_retry_stats(self, workflow_id: str) -> dict[str, int]:
        """Count of node_executions that required at least one retry
        (attempt_number > 1), per node_key — a real signal of which node
        types are flaky in production, not a synthesized guess."""
        executions = await self.repos.executions.list_for_workflow(workflow_id, limit=10_000)
        by_node: dict[str, int] = {}
        for execution in executions:
            for ne in await self.repos.node_executions.list_for_execution(execution.id):
                if ne.attempt_number > 1:
                    by_node[ne.node_key] = by_node.get(ne.node_key, 0) + 1
        return by_node

    async def get_token_usage(self, workflow_id: str) -> dict:
        """Real token counts logged by every LLM_CALL node's actual AI
        Core response — not an estimate. Dollar cost is a natural
        follow-on once AI Core's `CostCalculator` is threaded through the
        Execution Engine; that wiring doesn't exist yet, so this reports
        tokens (real) rather than a fabricated cost figure."""
        executions = await self.repos.executions.list_for_workflow(workflow_id, limit=10_000)
        input_tokens = 0
        output_tokens = 0
        llm_call_count = 0
        for execution in executions:
            for ne in await self.repos.node_executions.list_for_execution(execution.id):
                if ne.node_type != "llm_call" or ne.status != "succeeded":
                    continue
                llm_call_count += 1
                input_tokens += ne.output_data.get("input_tokens", 0) or 0
                output_tokens += ne.output_data.get("output_tokens", 0) or 0
        return {
            "workflow_id": workflow_id, "llm_call_count": llm_call_count,
            "total_input_tokens": input_tokens, "total_output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
