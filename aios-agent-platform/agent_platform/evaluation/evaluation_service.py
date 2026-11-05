"""Evaluation-lite: task success rate, planning quality, a reasoning
quality proxy, tool effectiveness, reliability, collaboration quality,
and failure recovery rate — every metric here is computed directly from
already-persisted observability rows (executions, tasks, messages,
reasoning traces). No LLM-judge calls, no separate evaluation-run
pipeline, no golden test cases — that's the Enterprise Evaluation
platform the agent platform scope boundary explicitly excludes. What's here is
real arithmetic over real data, not a stub.
"""
from __future__ import annotations

from agent_platform.domain.enums import TaskStatus
from agent_platform.repositories.registry import RepositoryRegistry


class EvaluationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def task_success_rate(self, root_task_id: str) -> dict:
        tasks = await self.repos.tasks.list_for_root(root_task_id)
        children = [t for t in tasks if t.id != root_task_id] or tasks
        total = len(children)
        completed = sum(1 for t in children if t.status == TaskStatus.COMPLETED.value)
        failed = sum(1 for t in children if t.status == TaskStatus.FAILED.value)
        return {
            "total": total, "completed": completed, "failed": failed,
            "success_rate": round(completed / total * 100, 2) if total else 0.0,
        }

    async def planning_quality(self, root_task_id: str) -> dict:
        """Proxy signal: a plan whose subtasks mostly ran to completion as
        originally decomposed is judged higher quality than one that
        needed a lot of cancellation/replanning — computed from task
        status alone, no judge call."""
        tasks = await self.repos.tasks.list_for_root(root_task_id)
        children = [t for t in tasks if t.id != root_task_id]
        if not children:
            return {"subtask_count": 0, "cancelled_ratio": 0.0, "quality_score": 1.0}
        cancelled = sum(1 for t in children if t.status == TaskStatus.CANCELLED.value)
        cancelled_ratio = cancelled / len(children)
        return {"subtask_count": len(children), "cancelled_ratio": round(cancelled_ratio, 2), "quality_score": round(1.0 - cancelled_ratio, 2)}

    async def reasoning_quality_proxy(self, task_id: str) -> dict:
        """A proxy, not a ground-truth score: average self-reported (and
        attempt-adjusted) confidence across a task's reasoning traces."""
        traces = await self.repos.reasoning_traces.list_for_task(task_id)
        if not traces:
            return {"trace_count": 0, "avg_confidence": None}
        avg_confidence = sum(t.confidence or 0.0 for t in traces) / len(traces)
        return {"trace_count": len(traces), "avg_confidence": round(avg_confidence, 3)}

    async def tool_effectiveness(self, agent_id: str) -> dict:
        executions = await self.repos.executions.list_for_agent(agent_id, limit=500)
        with_tools = [e for e in executions if e.tool_calls_count > 0]
        if not with_tools:
            return {"executions_using_tools": 0, "tool_success_rate": None}
        successful = sum(1 for e in with_tools if e.success)
        return {"executions_using_tools": len(with_tools), "tool_success_rate": round(successful / len(with_tools) * 100, 2)}

    async def reliability(self, agent_id: str) -> dict:
        """Success rate plus retry burden — succeeding only after several
        retries is a weaker reliability signal than succeeding cleanly."""
        executions = await self.repos.executions.list_for_agent(agent_id, limit=500)
        if not executions:
            return {"execution_count": 0, "success_rate": 0.0, "avg_retries": 0.0}
        success_rate = await self.repos.executions.success_rate(agent_id)
        avg_retries = sum(e.retry_count for e in executions) / len(executions)
        return {"execution_count": len(executions), "success_rate": success_rate, "avg_retries": round(avg_retries, 2)}

    async def collaboration_quality(self, task_id: str) -> dict:
        """A proxy from the message trail: how many distinct agents
        contributed and how much they communicated — real counts, not a
        judged score of how well they collaborated."""
        messages = await self.repos.messages.list_for_task(task_id)
        participants = {m.from_agent_id for m in messages if m.from_agent_id} | {m.to_agent_id for m in messages if m.to_agent_id}
        return {"message_count": len(messages), "distinct_agents": len(participants)}

    async def failure_recovery_rate(self, agent_id: str) -> dict:
        """Of the tasks where this agent had at least one failed
        execution, what fraction ended in that same task's most recent
        execution succeeding — a real measure of whether retry/recovery
        actually worked, not a judge score."""
        executions = await self.repos.executions.list_for_agent(agent_id, limit=500)
        by_task: dict[str, list] = {}
        for e in executions:
            if e.task_id:
                by_task.setdefault(e.task_id, []).append(e)

        had_failure = 0
        recovered = 0
        for task_executions in by_task.values():
            ordered = sorted(task_executions, key=lambda e: e.started_at)
            if any(not e.success for e in ordered):
                had_failure += 1
                if ordered[-1].success:
                    recovered += 1

        rate = round(recovered / had_failure * 100, 2) if had_failure else None
        return {"tasks_with_failure": had_failure, "recovered": recovered, "failure_recovery_rate": rate}
