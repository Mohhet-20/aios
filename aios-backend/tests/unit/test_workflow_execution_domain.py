from datetime import datetime, timezone

import pytest

from app.domain.entities.workflow import WorkflowExecution
from app.domain.exceptions import UnprocessableStateError
from app.domain.value_objects.enums import ExecutionStatus


def make_execution(status: ExecutionStatus = ExecutionStatus.PENDING) -> WorkflowExecution:
    return WorkflowExecution(
        id="e1",
        workflow_id="w1",
        status=status,
        triggered_by="u1",
        input_payload={},
        started_at=datetime.now(timezone.utc),
    )


def test_pending_to_running_is_allowed():
    execution = make_execution()
    execution.transition(ExecutionStatus.RUNNING)
    assert execution.status == ExecutionStatus.RUNNING
    assert not execution.is_terminal


def test_completed_is_terminal_and_sets_completed_at():
    execution = make_execution(ExecutionStatus.RUNNING)
    execution.transition(ExecutionStatus.COMPLETED)
    assert execution.is_terminal
    assert execution.completed_at is not None
    assert execution.duration_ms is not None


def test_cannot_transition_from_completed():
    execution = make_execution(ExecutionStatus.COMPLETED)
    with pytest.raises(UnprocessableStateError):
        execution.transition(ExecutionStatus.RUNNING)


def test_waiting_for_human_then_resume():
    execution = make_execution(ExecutionStatus.RUNNING)
    execution.transition(ExecutionStatus.WAITING_FOR_HUMAN)
    execution.transition(ExecutionStatus.RUNNING)
    execution.transition(ExecutionStatus.COMPLETED)
    assert execution.status == ExecutionStatus.COMPLETED
