"""Workflow execution aggregate — models the execution state machine
described in the Phase 1 Workflow Engine design (pending -> running ->
completed/failed/cancelled, with an optional waiting-for-human pause).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.clock import utc_now
from app.domain.exceptions import UnprocessableStateError
from app.domain.value_objects.enums import ExecutionStatus

_ALLOWED_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.RUNNING: {
        ExecutionStatus.WAITING_FOR_HUMAN,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    ExecutionStatus.WAITING_FOR_HUMAN: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.COMPLETED: set(),
    ExecutionStatus.FAILED: set(),
    ExecutionStatus.CANCELLED: set(),
}

TERMINAL_STATUSES = {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}


@dataclass
class WorkflowStepResult:
    step_id: str
    step_type: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None = None
    output: dict | None = None
    error: str | None = None


@dataclass
class WorkflowExecution:
    id: str
    workflow_id: str
    status: ExecutionStatus
    triggered_by: str
    input_payload: dict
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[WorkflowStepResult] = field(default_factory=list)
    error: str | None = None

    def transition(self, target: ExecutionStatus) -> None:
        if target not in _ALLOWED_TRANSITIONS.get(self.status, set()):
            raise UnprocessableStateError(
                f"Cannot transition workflow execution from {self.status.value} to {target.value}",
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target
        if target in TERMINAL_STATUSES:
            self.completed_at = utc_now()

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def duration_ms(self) -> float | None:
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000


@dataclass
class Workflow:
    id: str
    workspace_id: str
    name: str
    description: str
    status: str
    definition: dict  # {"nodes": [...], "edges": [...]} — validated by WorkflowService
    success_rate: float = 0.0
