"""ExecutionStateService: read-side views over an execution's state —
its current position in the graph, its live context, and lightweight
metadata about the run so far. Distinct from Observability (Task 93),
which aggregates timing/cost/failure metrics across many executions;
this service answers "what does this one execution's state look like
right now," the same question a Variable Explorer or an Execution
Replay frontend surface would ask on every render."""
from __future__ import annotations

from workflow_platform.repositories.registry import RepositoryRegistry


class ExecutionStateService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_state_snapshot(self, execution_id: str) -> dict:
        execution = await self.repos.executions.get_or_404(execution_id)
        latest_checkpoint = await self.repos.checkpoints.get_latest_for_execution(execution_id)
        return {
            "execution_id": execution.id,
            "status": execution.status,
            "current_node_key": execution.current_node_key,
            "context_variables": dict(execution.context_variables),
            "input_variables": dict(execution.input_variables),
            "output_variables": dict(execution.output_variables),
            "recursion_depth": execution.recursion_depth,
            "parent_execution_id": execution.parent_execution_id,
            "latest_checkpoint_sequence": latest_checkpoint.sequence_number if latest_checkpoint else None,
        }

    async def get_execution_metadata(self, execution_id: str) -> dict:
        execution = await self.repos.executions.get_or_404(execution_id)
        node_executions = await self.repos.node_executions.list_for_execution(execution_id)
        checkpoints = await self.repos.checkpoints.list_for_execution(execution_id)

        duration_ms = None
        if execution.started_at is not None:
            end = execution.completed_at or None
            if end is not None:
                started = execution.started_at
                if started.tzinfo is None:
                    from datetime import timezone
                    started = started.replace(tzinfo=timezone.utc)
                if end.tzinfo is None:
                    from datetime import timezone
                    end = end.replace(tzinfo=timezone.utc)
                duration_ms = (end - started).total_seconds() * 1000

        return {
            "execution_id": execution.id,
            "status": execution.status,
            "node_execution_count": len(node_executions),
            "succeeded_node_count": sum(1 for ne in node_executions if ne.status == "succeeded"),
            "failed_node_count": sum(1 for ne in node_executions if ne.status == "failed"),
            "checkpoint_count": len(checkpoints),
            "duration_ms": duration_ms,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        }
