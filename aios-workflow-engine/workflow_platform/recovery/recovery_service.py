"""RecoveryService: the checkpoint-storage half of State Management —
rewinding a RUNNING or PAUSED execution's `context_variables`/
`current_node_key` back to a known-good `CheckpointModel` snapshot, and
sweeping for executions that look "stalled" (still RUNNING in the
database, but with no progress recorded in a suspiciously long time —
the signature of a process that crashed mid-run rather than one that's
genuinely still working). Recovered executions land in PAUSED, never
auto-resumed — an operator (or an automated policy built on top of this
service) decides whether to `resume_execution` or `cancel_execution`
from there, matching this platform's general bias toward explicit
control over destructive-feeling automatic action."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from workflow_platform.core.exceptions import NotFoundError, ValidationError
from workflow_platform.database.base import utcnow
from workflow_platform.domain.enums import ExecutionStatus
from workflow_platform.models.checkpoint import CheckpointModel
from workflow_platform.models.execution import ExecutionModel
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_engine.mappers import apply_execution_domain_to_model, execution_to_domain


def _as_aware(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip — every timestamp this platform
    writes is UTC, so a naive value is safely treated as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class RecoveryService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def list_checkpoints(self, execution_id: str) -> list[CheckpointModel]:
        return await self.repos.checkpoints.list_for_execution(execution_id)

    async def get_latest_checkpoint(self, execution_id: str) -> CheckpointModel | None:
        return await self.repos.checkpoints.get_latest_for_execution(execution_id)

    async def restore_from_checkpoint(self, execution_id: str, *, sequence_number: int | None = None) -> ExecutionModel:
        execution = await self.repos.executions.get_or_404(execution_id)
        if execution.status not in (ExecutionStatus.RUNNING.value, ExecutionStatus.PAUSED.value):
            raise ValidationError(
                f"can only restore a RUNNING or PAUSED execution from a checkpoint (status: {execution.status})"
            )

        if sequence_number is None:
            checkpoint = await self.repos.checkpoints.get_latest_for_execution(execution_id)
        else:
            checkpoints = await self.repos.checkpoints.list_for_execution(execution_id)
            checkpoint = next((c for c in checkpoints if c.sequence_number == sequence_number), None)
        if checkpoint is None:
            detail = f" at sequence {sequence_number}" if sequence_number is not None else ""
            raise NotFoundError(f"no checkpoint found for execution '{execution_id}'{detail}")

        execution.context_variables = dict(checkpoint.state_snapshot.get("context_variables", {}))
        execution.current_node_key = checkpoint.state_snapshot.get("current_node_key")

        if execution.status == ExecutionStatus.RUNNING.value:
            entity = execution_to_domain(execution)
            entity.pause()
            apply_execution_domain_to_model(entity, execution)

        return await self.repos.executions.update(execution)

    async def recover_stalled_executions(self, *, stalled_after_seconds: int, as_of: datetime | None = None) -> list[ExecutionModel]:
        as_of = as_of or utcnow()
        cutoff = as_of - timedelta(seconds=stalled_after_seconds)

        recovered: list[ExecutionModel] = []
        for execution in await self.repos.executions.list_by_status(ExecutionStatus.RUNNING.value):
            latest = await self.repos.checkpoints.get_latest_for_execution(execution.id)
            last_progress = latest.created_at if latest is not None else execution.started_at
            if last_progress is None or _as_aware(last_progress) >= cutoff:
                continue  # genuinely still working, or too new to judge

            try:
                recovered.append(await self.restore_from_checkpoint(execution.id))
            except NotFoundError:
                # stalled with no checkpoint yet — nothing to rewind to,
                # just pause it in place so it isn't left falsely RUNNING.
                entity = execution_to_domain(execution)
                entity.pause()
                apply_execution_domain_to_model(entity, execution)
                recovered.append(await self.repos.executions.update(execution))
        return recovered
