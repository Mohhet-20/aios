"""Observability: execution timelines, delegation chains, and agent
health — the read-side services the Execution Timeline / Delegation
Graph / Health Dashboard frontend surfaces would call. Every number here
is derived directly from already-persisted rows (AgentExecutionModel,
MessageModel, ReasoningTraceModel, ReflectionModel, DelegationModel) —
this module reads, it never writes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from agent_platform.repositories.registry import RepositoryRegistry


def _aware(ts: datetime) -> datetime:
    """SQLite has no native tz-aware storage, so a `DateTime(timezone=True)`
    column can round-trip as naive depending on whether the ORM served the
    value from its identity map (still aware, client-side default) or from
    a fresh row load (naive) — normalize to UTC-aware before ever comparing
    or sorting timestamps from mixed sources, rather than relying on which
    path any given row happened to come from."""
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)


class ObservabilityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def execution_timeline(self, task_id: str) -> list[dict]:
        """Every recorded thing that happened for a task, one unified,
        time-ordered feed — executions, messages, reasoning traces, and
        reflections all merged and tagged by `type` so a single call
        renders the whole timeline."""
        executions = await self.repos.executions.list_for_task(task_id)
        messages = await self.repos.messages.list_for_task(task_id)
        reasoning_traces = await self.repos.reasoning_traces.list_for_task(task_id)
        reflections = await self.repos.reflections.list_for_task(task_id)

        events: list[dict] = []
        for e in executions:
            events.append({
                "type": "execution", "timestamp": e.started_at, "agent_id": e.agent_id, "status": e.status,
                "success": e.success, "latency_ms": e.latency_ms, "cost_usd": e.cost_usd, "tool_calls_count": e.tool_calls_count,
            })
        for m in messages:
            events.append({
                "type": "message", "timestamp": m.created_at, "message_type": m.message_type,
                "from_agent_id": m.from_agent_id, "to_agent_id": m.to_agent_id, "content": m.content,
            })
        for r in reasoning_traces:
            events.append({
                "type": "reasoning", "timestamp": r.created_at, "agent_id": r.agent_id,
                "mode": r.mode, "branches_explored": r.branches_explored, "confidence": r.confidence,
            })
        for rf in reflections:
            events.append({
                "type": "reflection", "timestamp": rf.created_at, "agent_id": rf.reflecting_agent_id,
                "iteration": rf.iteration, "passed_verification": rf.passed_verification, "confidence": rf.confidence,
            })
        for event in events:
            event["timestamp"] = _aware(event["timestamp"])
        events.sort(key=lambda ev: ev["timestamp"])
        return events

    async def delegation_chain(self, task_id: str) -> list[dict]:
        delegations = await self.repos.delegations.list_for_task(task_id)
        return [
            {
                "id": d.id, "from_agent_id": d.from_agent_id, "to_agent_id": d.to_agent_id, "status": d.status,
                "reason": d.reason, "created_at": d.created_at, "accepted_at": d.accepted_at, "completed_at": d.completed_at,
            }
            for d in delegations
        ]

    async def agent_health_summary(self, agent_id: str) -> dict:
        agent = await self.repos.agents.get_or_404(agent_id)
        executions = await self.repos.executions.list_for_agent(agent_id, limit=500)
        success_rate = await self.repos.executions.success_rate(agent_id)
        total_cost = sum(e.cost_usd for e in executions)
        total_tokens = sum(e.input_tokens + e.output_tokens for e in executions)
        avg_latency = (sum(e.latency_ms for e in executions) / len(executions)) if executions else 0.0
        return {
            "agent_id": agent.id, "name": agent.name, "lifecycle_status": agent.status, "health_status": agent.health_status,
            "execution_count": len(executions), "success_rate": success_rate,
            "total_cost_usd": round(total_cost, 6), "total_tokens": total_tokens, "avg_latency_ms": round(avg_latency, 2),
        }
