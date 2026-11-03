"""Analytics: latency/cost/token rollups over a set of executions —
mirrors the Prompt Platform's own p50/p95/p99 rollup pattern, scoped here
to an agent or a task instead of a prompt.
"""
from __future__ import annotations

from agent_platform.repositories.registry import RepositoryRegistry


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, round(p * (len(sorted_values) - 1)))
    return sorted_values[index]


class AnalyticsService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def cost_rollup(self, *, agent_id: str | None = None, task_id: str | None = None) -> dict:
        if agent_id is not None:
            executions = await self.repos.executions.list_for_agent(agent_id, limit=1000)
        elif task_id is not None:
            executions = await self.repos.executions.list_for_task(task_id)
        else:
            raise ValueError("cost_rollup requires either agent_id or task_id")

        latencies = sorted(e.latency_ms for e in executions)
        return {
            "count": len(executions),
            "total_cost_usd": round(sum(e.cost_usd for e in executions), 6),
            "total_input_tokens": sum(e.input_tokens for e in executions),
            "total_output_tokens": sum(e.output_tokens for e in executions),
            "latency_p50_ms": round(_percentile(latencies, 0.50), 2),
            "latency_p95_ms": round(_percentile(latencies, 0.95), 2),
            "latency_p99_ms": round(_percentile(latencies, 0.99), 2),
            "success_count": sum(1 for e in executions if e.success),
            "failure_count": sum(1 for e in executions if not e.success),
        }
