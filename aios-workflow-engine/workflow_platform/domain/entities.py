"""Pure-Python domain aggregates — no ORM/SQLAlchemy imports here, same
separation every prior AIOS platform used. `Workflow` owns the
publish/pause/archive lifecycle; `Execution` owns the real run-time
state machine (the core of the whole engine); `NodeExecution` owns
per-node retry/approval/timeout transitions; `ApprovalRequest` owns the
human-in-the-loop decision lifecycle; `Schedule` owns trigger lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from workflow_platform.core.exceptions import InvalidTransitionError, ValidationError
from workflow_platform.domain.enums import (
    ApprovalStatus,
    ExecutionStatus,
    NodeExecutionStatus,
    ScheduleStatus,
    WorkflowStatus,
)
from workflow_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


# -- Workflow -----------------------------------------------------------------------

_WORKFLOW_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
    WorkflowStatus.DRAFT: {WorkflowStatus.ACTIVE, WorkflowStatus.ARCHIVED},
    WorkflowStatus.ACTIVE: {WorkflowStatus.PAUSED, WorkflowStatus.ARCHIVED, WorkflowStatus.DEPRECATED},
    WorkflowStatus.PAUSED: {WorkflowStatus.ACTIVE, WorkflowStatus.ARCHIVED},
    WorkflowStatus.DEPRECATED: {WorkflowStatus.ARCHIVED},
    WorkflowStatus.ARCHIVED: set(),
}


@dataclass
class Workflow:
    id: str
    workspace_id: str
    name: str
    slug: str
    owner_id: str
    category: str
    description: str | None = None
    tags: list = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    priority: str = "normal"
    current_version_id: str | None = None
    variables: dict = field(default_factory=dict)
    workflow_metadata: dict = field(default_factory=dict)

    def _transition(self, target: WorkflowStatus) -> None:
        allowed = _WORKFLOW_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Workflow '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def publish(self, version_id: str) -> None:
        """Publishing a *new* version of an already-ACTIVE or PAUSED workflow
        just repoints `current_version_id` without disturbing status — status
        is only ever driven by publish/pause/resume/deprecate/archive, not by
        how many versions have shipped. Publishing a workflow's first version
        (from DRAFT) is the one case that also flips status to ACTIVE."""
        if not version_id:
            raise ValidationError("cannot publish a workflow without a version")
        if self.status in (WorkflowStatus.ACTIVE, WorkflowStatus.PAUSED):
            self.current_version_id = version_id
            return
        self._transition(WorkflowStatus.ACTIVE)
        self.current_version_id = version_id

    def pause(self) -> None:
        self._transition(WorkflowStatus.PAUSED)

    def resume(self) -> None:
        if self.status != WorkflowStatus.PAUSED:
            raise InvalidTransitionError(f"Workflow '{self.id}' can only resume from PAUSED (status: {self.status.value})")
        self._transition(WorkflowStatus.ACTIVE)

    def deprecate(self) -> None:
        self._transition(WorkflowStatus.DEPRECATED)

    def archive(self) -> None:
        self._transition(WorkflowStatus.ARCHIVED)


# -- Execution ------------------------------------------------------------------------

_EXECUTION_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.RUNNING: {
        ExecutionStatus.PAUSED, ExecutionStatus.WAITING_APPROVAL, ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED, ExecutionStatus.CANCELLED, ExecutionStatus.TIMED_OUT,
    },
    ExecutionStatus.PAUSED: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.WAITING_APPROVAL: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED, ExecutionStatus.FAILED},
    ExecutionStatus.FAILED: {ExecutionStatus.COMPENSATING},
    ExecutionStatus.TIMED_OUT: {ExecutionStatus.COMPENSATING, ExecutionStatus.CANCELLED},
    ExecutionStatus.COMPENSATING: {ExecutionStatus.COMPENSATED, ExecutionStatus.FAILED},
    ExecutionStatus.COMPENSATED: set(),
    ExecutionStatus.COMPLETED: set(),
    ExecutionStatus.CANCELLED: set(),
}

_EXECUTION_TERMINAL = {ExecutionStatus.COMPLETED, ExecutionStatus.CANCELLED, ExecutionStatus.COMPENSATED}


@dataclass
class Execution:
    id: str
    workflow_id: str
    workflow_version_id: str
    workspace_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    priority: str = "normal"
    trigger_type: str = "manual"
    triggered_by: str | None = None
    input_variables: dict = field(default_factory=dict)
    output_variables: dict = field(default_factory=dict)
    context_variables: dict = field(default_factory=dict)
    current_node_key: str | None = None
    parent_execution_id: str | None = None
    recursion_depth: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    timeout_at: datetime | None = None

    def _transition(self, target: ExecutionStatus) -> None:
        allowed = _EXECUTION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Execution '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def is_terminal(self) -> bool:
        return self.status in _EXECUTION_TERMINAL

    def start(self) -> None:
        self._transition(ExecutionStatus.RUNNING)
        self.started_at = _now()

    def pause(self) -> None:
        self._transition(ExecutionStatus.PAUSED)

    def resume(self) -> None:
        if self.status not in (ExecutionStatus.PAUSED, ExecutionStatus.WAITING_APPROVAL):
            raise InvalidTransitionError(f"Execution '{self.id}' can only resume from PAUSED/WAITING_APPROVAL (status: {self.status.value})")
        self._transition(ExecutionStatus.RUNNING)

    def request_approval(self) -> None:
        self._transition(ExecutionStatus.WAITING_APPROVAL)

    def complete(self, output_variables: dict | None = None) -> None:
        self._transition(ExecutionStatus.COMPLETED)
        if output_variables is not None:
            self.output_variables = output_variables
        self.completed_at = _now()

    def fail(self, error_message: str) -> None:
        self._transition(ExecutionStatus.FAILED)
        self.error_message = error_message
        self.completed_at = _now()

    def cancel(self) -> None:
        self._transition(ExecutionStatus.CANCELLED)
        self.completed_at = _now()

    def timeout(self, error_message: str | None = None) -> None:
        self._transition(ExecutionStatus.TIMED_OUT)
        self.error_message = error_message or self.error_message or "execution exceeded its configured timeout"
        self.completed_at = _now()

    def begin_compensation(self) -> None:
        self._transition(ExecutionStatus.COMPENSATING)

    def complete_compensation(self) -> None:
        self._transition(ExecutionStatus.COMPENSATED)
        self.completed_at = _now()

    def compensation_failed(self, error_message: str) -> None:
        self._transition(ExecutionStatus.FAILED)
        self.error_message = error_message
        self.completed_at = _now()

    def retry_from_node(self, node_key: str) -> None:
        """Operator-driven override: re-enters RUNNING from a FAILED or
        CANCELLED execution at a specific node, after whatever caused the
        original failure has been fixed externally (bad config, a
        transient dependency outage, etc). Deliberately not in
        `_EXECUTION_TRANSITIONS` alongside the automatic lifecycle
        transitions — this is an explicit administrative action, not
        something the run loop does on its own, so it gets its own
        narrowly-scoped guard rather than widening the general table."""
        if self.status not in (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            raise InvalidTransitionError(
                f"Execution '{self.id}' can only retry_from_node from FAILED/CANCELLED (status: {self.status.value})"
            )
        self.status = ExecutionStatus.RUNNING
        self.current_node_key = node_key
        self.error_message = None
        self.completed_at = None


# -- NodeExecution --------------------------------------------------------------------

_NODE_EXECUTION_TRANSITIONS: dict[NodeExecutionStatus, set[NodeExecutionStatus]] = {
    NodeExecutionStatus.PENDING: {NodeExecutionStatus.RUNNING, NodeExecutionStatus.SKIPPED, NodeExecutionStatus.CANCELLED},
    NodeExecutionStatus.RUNNING: {
        NodeExecutionStatus.SUCCEEDED, NodeExecutionStatus.FAILED, NodeExecutionStatus.TIMED_OUT,
        NodeExecutionStatus.WAITING_APPROVAL, NodeExecutionStatus.CANCELLED,
    },
    NodeExecutionStatus.FAILED: {NodeExecutionStatus.RETRYING, NodeExecutionStatus.CANCELLED},
    NodeExecutionStatus.TIMED_OUT: {NodeExecutionStatus.RETRYING, NodeExecutionStatus.CANCELLED},
    NodeExecutionStatus.RETRYING: {NodeExecutionStatus.RUNNING, NodeExecutionStatus.FAILED},
    NodeExecutionStatus.WAITING_APPROVAL: {NodeExecutionStatus.RUNNING, NodeExecutionStatus.SKIPPED, NodeExecutionStatus.CANCELLED},
    NodeExecutionStatus.SUCCEEDED: set(),
    NodeExecutionStatus.SKIPPED: set(),
    NodeExecutionStatus.CANCELLED: set(),
}


@dataclass
class NodeExecution:
    id: str
    execution_id: str
    node_key: str
    node_type: str
    status: NodeExecutionStatus = NodeExecutionStatus.PENDING
    attempt_number: int = 1
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None

    def _transition(self, target: NodeExecutionStatus) -> None:
        allowed = _NODE_EXECUTION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"NodeExecution '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(NodeExecutionStatus.RUNNING)
        self.started_at = _now()

    def succeed(self, output_data: dict | None = None) -> None:
        self._transition(NodeExecutionStatus.SUCCEEDED)
        if output_data is not None:
            self.output_data = output_data
        self._finish()

    def fail(self, error_message: str) -> None:
        self._transition(NodeExecutionStatus.FAILED)
        self.error_message = error_message
        self._finish()

    def timeout(self, error_message: str | None = None) -> None:
        self._transition(NodeExecutionStatus.TIMED_OUT)
        self.error_message = error_message or self.error_message or "node exceeded its configured timeout"
        self._finish()

    def retry(self) -> None:
        if self.status not in (NodeExecutionStatus.FAILED, NodeExecutionStatus.TIMED_OUT):
            raise InvalidTransitionError(f"NodeExecution '{self.id}' can only retry from FAILED/TIMED_OUT (status: {self.status.value})")
        self._transition(NodeExecutionStatus.RETRYING)
        self.attempt_number += 1

    def resume_after_retry(self) -> None:
        if self.status != NodeExecutionStatus.RETRYING:
            raise InvalidTransitionError(f"NodeExecution '{self.id}' must be RETRYING to resume (status: {self.status.value})")
        self._transition(NodeExecutionStatus.RUNNING)
        self.started_at = _now()

    def exhaust_retries(self, error_message: str) -> None:
        if self.status != NodeExecutionStatus.RETRYING:
            raise InvalidTransitionError(f"NodeExecution '{self.id}' must be RETRYING to exhaust (status: {self.status.value})")
        self._transition(NodeExecutionStatus.FAILED)
        self.error_message = error_message
        self._finish()

    def wait_for_approval(self) -> None:
        self._transition(NodeExecutionStatus.WAITING_APPROVAL)

    def resume_after_approval(self, *, approved: bool) -> None:
        if self.status != NodeExecutionStatus.WAITING_APPROVAL:
            raise InvalidTransitionError(f"NodeExecution '{self.id}' must be WAITING_APPROVAL to resume (status: {self.status.value})")
        if approved:
            self._transition(NodeExecutionStatus.RUNNING)
            self.started_at = _now()
        else:
            self._transition(NodeExecutionStatus.SKIPPED)
            self._finish()

    def skip(self) -> None:
        self._transition(NodeExecutionStatus.SKIPPED)
        self._finish()

    def cancel(self) -> None:
        self._transition(NodeExecutionStatus.CANCELLED)
        self._finish()

    def _finish(self) -> None:
        self.completed_at = _now()
        if self.started_at is not None:
            # SQLite drops tzinfo on DateTime round-trip, so a `started_at`
            # reloaded from the database (rather than set moments ago by
            # `start()`/`resume_after_retry()` in the same process) can
            # come back naive. Every timestamp this platform writes is UTC
            # (`database.base.utcnow`), so a naive value is safely treated
            # as UTC rather than left to blow up the subtraction below.
            started_at = self.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            self.duration_ms = (self.completed_at - started_at).total_seconds() * 1000


# -- ApprovalRequest --------------------------------------------------------------------

_APPROVAL_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.PENDING: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.ESCALATED, ApprovalStatus.EXPIRED, ApprovalStatus.CANCELLED},
    ApprovalStatus.ESCALATED: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED, ApprovalStatus.CANCELLED},
    ApprovalStatus.APPROVED: set(),
    ApprovalStatus.REJECTED: set(),
    ApprovalStatus.EXPIRED: set(),
    ApprovalStatus.CANCELLED: set(),
}


@dataclass
class ApprovalRequest:
    id: str
    execution_id: str
    node_execution_id: str
    workspace_id: str
    requested_by: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approval_chain: list = field(default_factory=list)
    current_step: int = 0
    reason: str | None = None
    sensitivity_level: str = "normal"
    decided_by: str | None = None
    decision_notes: str | None = None
    escalated_at: datetime | None = None
    decided_at: datetime | None = None

    def _transition(self, target: ApprovalStatus) -> None:
        allowed = _APPROVAL_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ApprovalRequest '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def advance_step(self) -> bool:
        """Returns True if there's a next step to wait on, False if the
        chain is fully satisfied (final approval)."""
        self.current_step += 1
        return self.current_step < len(self.approval_chain)

    def approve(self, *, decided_by: str, notes: str | None = None) -> None:
        self._transition(ApprovalStatus.APPROVED)
        self.decided_by = decided_by
        self.decision_notes = notes
        self.decided_at = _now()

    def reject(self, *, decided_by: str, notes: str | None = None) -> None:
        self._transition(ApprovalStatus.REJECTED)
        self.decided_by = decided_by
        self.decision_notes = notes
        self.decided_at = _now()

    def escalate(self) -> None:
        self._transition(ApprovalStatus.ESCALATED)
        self.escalated_at = _now()

    def expire(self) -> None:
        self._transition(ApprovalStatus.EXPIRED)

    def cancel(self) -> None:
        self._transition(ApprovalStatus.CANCELLED)


# -- Schedule -----------------------------------------------------------------------------

_SCHEDULE_TRANSITIONS: dict[ScheduleStatus, set[ScheduleStatus]] = {
    ScheduleStatus.ACTIVE: {ScheduleStatus.PAUSED, ScheduleStatus.CANCELLED, ScheduleStatus.COMPLETED},
    ScheduleStatus.PAUSED: {ScheduleStatus.ACTIVE, ScheduleStatus.CANCELLED},
    ScheduleStatus.COMPLETED: set(),
    ScheduleStatus.CANCELLED: set(),
}


@dataclass
class Schedule:
    id: str
    workflow_id: str
    workspace_id: str
    schedule_type: str
    created_by: str
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    cron_expression: str | None = None
    interval_seconds: int | None = None
    run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    run_count: int = 0

    def _transition(self, target: ScheduleStatus) -> None:
        allowed = _SCHEDULE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Schedule '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def pause(self) -> None:
        self._transition(ScheduleStatus.PAUSED)

    def resume(self) -> None:
        if self.status != ScheduleStatus.PAUSED:
            raise InvalidTransitionError(f"Schedule '{self.id}' can only resume from PAUSED (status: {self.status.value})")
        self._transition(ScheduleStatus.ACTIVE)

    def cancel(self) -> None:
        self._transition(ScheduleStatus.CANCELLED)

    def complete(self) -> None:
        self._transition(ScheduleStatus.COMPLETED)

    def record_run(self, *, next_run_at: datetime | None) -> None:
        if self.status != ScheduleStatus.ACTIVE:
            raise InvalidTransitionError(f"Schedule '{self.id}' must be ACTIVE to record a run (status: {self.status.value})")
        self.last_run_at = _now()
        self.run_count += 1
        self.next_run_at = next_run_at
        if next_run_at is None:
            self.complete()
