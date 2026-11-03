import pytest

from workflow_platform.core.exceptions import InvalidTransitionError, ValidationError
from workflow_platform.domain.entities import (
    ApprovalRequest,
    Execution,
    NodeExecution,
    Schedule,
    Workflow,
)
from workflow_platform.domain.enums import (
    ApprovalStatus,
    ExecutionStatus,
    NodeExecutionStatus,
    ScheduleStatus,
    WorkflowStatus,
)


def _workflow(**overrides):
    defaults = dict(id="wf-1", workspace_id="ws-1", name="My Workflow", slug="my-workflow", owner_id="user-1", category="automation")
    defaults.update(overrides)
    return Workflow(**defaults)


def _execution(**overrides):
    defaults = dict(id="exec-1", workflow_id="wf-1", workflow_version_id="v-1", workspace_id="ws-1")
    defaults.update(overrides)
    return Execution(**defaults)


def _node_execution(**overrides):
    defaults = dict(id="ne-1", execution_id="exec-1", node_key="call_llm", node_type="llm_call")
    defaults.update(overrides)
    return NodeExecution(**defaults)


def _approval(**overrides):
    defaults = dict(id="ap-1", execution_id="exec-1", node_execution_id="ne-1", workspace_id="ws-1", requested_by="user-1", approval_chain=[["mgr-1"], ["fin-1", "fin-2"]])
    defaults.update(overrides)
    return ApprovalRequest(**defaults)


def _schedule(**overrides):
    defaults = dict(id="sch-1", workflow_id="wf-1", workspace_id="ws-1", schedule_type="cron", created_by="user-1")
    defaults.update(overrides)
    return Schedule(**defaults)


# -- Workflow -------------------------------------------------------------------------

def test_workflow_defaults_draft():
    wf = _workflow()
    assert wf.status == WorkflowStatus.DRAFT


def test_workflow_publish_sets_active_and_version():
    wf = _workflow()
    wf.publish("v-1")
    assert wf.status == WorkflowStatus.ACTIVE
    assert wf.current_version_id == "v-1"


def test_workflow_publish_without_version_rejected():
    wf = _workflow()
    with pytest.raises(ValidationError):
        wf.publish("")


def test_workflow_pause_and_resume():
    wf = _workflow()
    wf.publish("v-1")
    wf.pause()
    assert wf.status == WorkflowStatus.PAUSED
    wf.resume()
    assert wf.status == WorkflowStatus.ACTIVE


def test_workflow_republish_while_active_repoints_without_status_change():
    wf = _workflow()
    wf.publish("v-1")
    assert wf.status == WorkflowStatus.ACTIVE
    wf.publish("v-2")
    assert wf.status == WorkflowStatus.ACTIVE
    assert wf.current_version_id == "v-2"


def test_workflow_republish_while_paused_stays_paused():
    wf = _workflow()
    wf.publish("v-1")
    wf.pause()
    wf.publish("v-2")
    assert wf.status == WorkflowStatus.PAUSED
    assert wf.current_version_id == "v-2"


def test_workflow_resume_requires_paused():
    wf = _workflow()
    with pytest.raises(InvalidTransitionError):
        wf.resume()


def test_workflow_archive_from_draft():
    wf = _workflow()
    wf.archive()
    assert wf.status == WorkflowStatus.ARCHIVED


def test_workflow_archived_is_terminal():
    wf = _workflow()
    wf.archive()
    with pytest.raises(InvalidTransitionError):
        wf.publish("v-1")


def test_workflow_deprecate_then_archive():
    wf = _workflow()
    wf.publish("v-1")
    wf.deprecate()
    assert wf.status == WorkflowStatus.DEPRECATED
    wf.archive()
    assert wf.status == WorkflowStatus.ARCHIVED


# -- Execution ---------------------------------------------------------------------------

def test_execution_defaults_pending():
    ex = _execution()
    assert ex.status == ExecutionStatus.PENDING


def test_execution_start_sets_started_at():
    ex = _execution()
    ex.start()
    assert ex.status == ExecutionStatus.RUNNING
    assert ex.started_at is not None


def test_execution_pause_resume():
    ex = _execution()
    ex.start()
    ex.pause()
    assert ex.status == ExecutionStatus.PAUSED
    ex.resume()
    assert ex.status == ExecutionStatus.RUNNING


def test_execution_complete_sets_output_and_terminal():
    ex = _execution()
    ex.start()
    ex.complete({"result": "ok"})
    assert ex.status == ExecutionStatus.COMPLETED
    assert ex.output_variables == {"result": "ok"}
    assert ex.completed_at is not None
    assert ex.is_terminal()


def test_execution_fail_records_error():
    ex = _execution()
    ex.start()
    ex.fail("boom")
    assert ex.status == ExecutionStatus.FAILED
    assert ex.error_message == "boom"


def test_execution_cannot_complete_from_pending():
    ex = _execution()
    with pytest.raises(InvalidTransitionError):
        ex.complete()


def test_execution_waiting_approval_then_resume():
    ex = _execution()
    ex.start()
    ex.request_approval()
    assert ex.status == ExecutionStatus.WAITING_APPROVAL
    ex.resume()
    assert ex.status == ExecutionStatus.RUNNING


def test_execution_waiting_approval_rejected_fails():
    ex = _execution()
    ex.start()
    ex.request_approval()
    ex.fail("rejected by approver")
    assert ex.status == ExecutionStatus.FAILED


def test_execution_compensation_flow():
    ex = _execution()
    ex.start()
    ex.fail("node failed")
    ex.begin_compensation()
    assert ex.status == ExecutionStatus.COMPENSATING
    ex.complete_compensation()
    assert ex.status == ExecutionStatus.COMPENSATED
    assert ex.is_terminal()


def test_execution_compensation_can_itself_fail():
    ex = _execution()
    ex.start()
    ex.fail("node failed")
    ex.begin_compensation()
    ex.compensation_failed("rollback also failed")
    assert ex.status == ExecutionStatus.FAILED


def test_execution_timeout_then_compensate():
    ex = _execution()
    ex.start()
    ex.timeout()
    assert ex.status == ExecutionStatus.TIMED_OUT
    assert "timeout" in ex.error_message
    ex.begin_compensation()
    assert ex.status == ExecutionStatus.COMPENSATING


def test_execution_cancel_from_pending():
    ex = _execution()
    ex.cancel()
    assert ex.status == ExecutionStatus.CANCELLED
    assert ex.is_terminal()


# -- NodeExecution -----------------------------------------------------------------------

def test_node_execution_success_path():
    ne = _node_execution()
    ne.start()
    assert ne.status == NodeExecutionStatus.RUNNING
    ne.succeed({"output": 42})
    assert ne.status == NodeExecutionStatus.SUCCEEDED
    assert ne.output_data == {"output": 42}
    assert ne.duration_ms is not None


def test_node_execution_retry_loop():
    ne = _node_execution()
    ne.start()
    ne.fail("transient error")
    assert ne.status == NodeExecutionStatus.FAILED
    ne.retry()
    assert ne.status == NodeExecutionStatus.RETRYING
    assert ne.attempt_number == 2
    ne.resume_after_retry()
    assert ne.status == NodeExecutionStatus.RUNNING
    ne.succeed()
    assert ne.status == NodeExecutionStatus.SUCCEEDED


def test_node_execution_exhaust_retries():
    ne = _node_execution()
    ne.start()
    ne.fail("error")
    ne.retry()
    ne.exhaust_retries("gave up after 3 attempts")
    assert ne.status == NodeExecutionStatus.FAILED
    assert "gave up" in ne.error_message


def test_node_execution_approval_approved_resumes():
    ne = _node_execution()
    ne.start()
    ne.wait_for_approval()
    assert ne.status == NodeExecutionStatus.WAITING_APPROVAL
    ne.resume_after_approval(approved=True)
    assert ne.status == NodeExecutionStatus.RUNNING


def test_node_execution_approval_rejected_skips():
    ne = _node_execution()
    ne.start()
    ne.wait_for_approval()
    ne.resume_after_approval(approved=False)
    assert ne.status == NodeExecutionStatus.SKIPPED


def test_node_execution_timeout():
    ne = _node_execution()
    ne.start()
    ne.timeout()
    assert ne.status == NodeExecutionStatus.TIMED_OUT
    assert ne.error_message is not None


def test_node_execution_cannot_retry_from_succeeded():
    ne = _node_execution()
    ne.start()
    ne.succeed()
    with pytest.raises(InvalidTransitionError):
        ne.retry()


# -- ApprovalRequest ----------------------------------------------------------------------

def test_approval_defaults_pending():
    ap = _approval()
    assert ap.status == ApprovalStatus.PENDING


def test_approval_approve():
    ap = _approval()
    ap.approve(decided_by="mgr-1", notes="looks good")
    assert ap.status == ApprovalStatus.APPROVED
    assert ap.decided_by == "mgr-1"
    assert ap.decided_at is not None


def test_approval_reject():
    ap = _approval()
    ap.reject(decided_by="mgr-1", notes="not now")
    assert ap.status == ApprovalStatus.REJECTED


def test_approval_escalate_then_approve():
    ap = _approval()
    ap.escalate()
    assert ap.status == ApprovalStatus.ESCALATED
    assert ap.escalated_at is not None
    ap.approve(decided_by="director-1")
    assert ap.status == ApprovalStatus.APPROVED


def test_approval_terminal_states_reject_further_transitions():
    ap = _approval()
    ap.approve(decided_by="mgr-1")
    with pytest.raises(InvalidTransitionError):
        ap.reject(decided_by="mgr-1")


def test_approval_advance_step_multi_step_chain():
    ap = _approval()
    assert ap.current_step == 0
    has_next = ap.advance_step()
    assert has_next is True
    assert ap.current_step == 1
    has_next = ap.advance_step()
    assert has_next is False  # chain of length 2 exhausted


def test_approval_expire_and_cancel():
    ap1 = _approval()
    ap1.expire()
    assert ap1.status == ApprovalStatus.EXPIRED

    ap2 = _approval()
    ap2.cancel()
    assert ap2.status == ApprovalStatus.CANCELLED


# -- Schedule -----------------------------------------------------------------------------

def test_schedule_defaults_active():
    sch = _schedule()
    assert sch.status == ScheduleStatus.ACTIVE


def test_schedule_pause_resume():
    sch = _schedule()
    sch.pause()
    assert sch.status == ScheduleStatus.PAUSED
    sch.resume()
    assert sch.status == ScheduleStatus.ACTIVE


def test_schedule_record_run_updates_counters():
    import datetime as dt
    sch = _schedule()
    next_run = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    sch.record_run(next_run_at=next_run)
    assert sch.run_count == 1
    assert sch.last_run_at is not None
    assert sch.next_run_at == next_run


def test_schedule_record_run_with_no_next_completes_it():
    sch = _schedule()
    sch.record_run(next_run_at=None)
    assert sch.status == ScheduleStatus.COMPLETED


def test_schedule_cancel():
    sch = _schedule()
    sch.cancel()
    assert sch.status == ScheduleStatus.CANCELLED
    with pytest.raises(InvalidTransitionError):
        sch.resume()
