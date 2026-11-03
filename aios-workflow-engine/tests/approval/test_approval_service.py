from datetime import timedelta

import pytest

from tests.approval.conftest import make_approval_workflow
from workflow_platform.core.exceptions import AuthorizationError, InvalidTransitionError
from workflow_platform.database.base import utcnow
from workflow_platform.domain.enums import ApprovalStatus, ExecutionStatus, NodeExecutionStatus


@pytest.mark.asyncio
async def test_single_step_approval_resumes_execution(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]], "reason": "needs sign-off"})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.WAITING_APPROVAL.value

    request = (await approval_service.list_for_execution(execution.id))[0]
    assert request.status == ApprovalStatus.PENDING.value

    decided = await approval_service.approve_step(request.id, decided_by="mgr-1", notes="looks good")
    assert decided.status == ApprovalStatus.APPROVED.value

    final_execution = await repos.executions.get_or_404(execution.id)
    assert final_execution.status == ExecutionStatus.COMPLETED.value

    approve_ne = next(ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "approve")
    assert approve_ne.status == NodeExecutionStatus.SUCCEEDED.value
    assert approve_ne.output_data["approved"] is True


@pytest.mark.asyncio
async def test_rejection_resumes_execution_with_approved_false(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    decided = await approval_service.reject(request.id, decided_by="mgr-1", notes="not now")
    assert decided.status == ApprovalStatus.REJECTED.value

    final_execution = await repos.executions.get_or_404(execution.id)
    assert final_execution.status == ExecutionStatus.COMPLETED.value  # workflow still routes onward past the rejected gate
    assert final_execution.output_variables.get("approved") is False

    approve_ne = next(ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "approve")
    assert approve_ne.status == NodeExecutionStatus.SKIPPED.value


@pytest.mark.asyncio
async def test_unauthorized_approver_rejected(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    with pytest.raises(AuthorizationError):
        await approval_service.approve_step(request.id, decided_by="random-person")


@pytest.mark.asyncio
async def test_multi_step_chain_requires_both_steps(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(
        workflow_service, version_service, workspace,
        approval_config={"approval_chain": [["mgr-1"], ["fin-1", "fin-2"]]},
    )
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    step1 = await approval_service.approve_step(request.id, decided_by="mgr-1")
    assert step1.status == ApprovalStatus.PENDING.value  # chain not exhausted yet
    assert step1.current_step == 1

    # execution should still be paused — step 2 hasn't happened
    mid_execution = await repos.executions.get_or_404(execution.id)
    assert mid_execution.status == ExecutionStatus.WAITING_APPROVAL.value

    # mgr-1 is no longer authorized for step 2
    with pytest.raises(AuthorizationError):
        await approval_service.approve_step(request.id, decided_by="mgr-1")

    step2 = await approval_service.approve_step(request.id, decided_by="fin-2")
    assert step2.status == ApprovalStatus.APPROVED.value

    final_execution = await repos.executions.get_or_404(execution.id)
    assert final_execution.status == ExecutionStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_rejection_at_any_step_kills_the_chain(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(
        workflow_service, version_service, workspace,
        approval_config={"approval_chain": [["mgr-1"], ["fin-1"]]},
    )
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    decided = await approval_service.reject(request.id, decided_by="mgr-1")
    assert decided.status == ApprovalStatus.REJECTED.value
    assert decided.current_step == 0  # never advanced past step 1

    final_execution = await repos.executions.get_or_404(execution.id)
    assert final_execution.status == ExecutionStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_reassign_step_changes_authorized_approvers(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    await approval_service.reassign_step(request.id, new_approvers=["mgr-2"], reassigned_by="admin")

    with pytest.raises(AuthorizationError):
        await approval_service.approve_step(request.id, decided_by="mgr-1")

    decided = await approval_service.approve_step(request.id, decided_by="mgr-2")
    assert decided.status == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_comments_can_be_added_and_listed(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    await approval_service.add_comment(request.id, author_id="mgr-1", comment="checking the numbers")
    await approval_service.add_comment(request.id, author_id="requester", comment="let me know if you need anything")

    comments = await approval_service.list_comments(request.id)
    assert len(comments) == 2
    assert comments[0].comment == "checking the numbers"


@pytest.mark.asyncio
async def test_escalation_sweep_escalates_overdue_requests(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(
        workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]], "escalate_after_seconds": 60},
    )
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]
    assert request.escalate_after is not None

    # not yet due
    escalated_early = await approval_service.run_escalation_sweep(as_of=utcnow())
    assert escalated_early == []

    escalated = await approval_service.run_escalation_sweep(as_of=utcnow() + timedelta(seconds=61))
    assert len(escalated) == 1
    assert escalated[0].status == ApprovalStatus.ESCALATED.value

    # escalated requests can still be approved
    decided = await approval_service.approve_step(request.id, decided_by="mgr-1")
    assert decided.status == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_expire_resumes_execution_as_not_approved(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    decided = await approval_service.expire(request.id)
    assert decided.status == ApprovalStatus.EXPIRED.value

    final_execution = await repos.executions.get_or_404(execution.id)
    assert final_execution.status == ExecutionStatus.COMPLETED.value
    assert final_execution.output_variables.get("expired") is True


@pytest.mark.asyncio
async def test_cannot_decide_an_already_decided_request(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    await approval_service.approve_step(request.id, decided_by="mgr-1")
    with pytest.raises(InvalidTransitionError):
        await approval_service.approve_step(request.id, decided_by="mgr-1")


@pytest.mark.asyncio
async def test_audit_log_records_decision(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    await approval_service.approve_step(request.id, decided_by="mgr-1")
    entries = await repos.audit_log.list_for_resource("approval_request", request.id)
    assert any(e.action == "approval_approved" for e in entries)


@pytest.mark.asyncio
async def test_events_published_for_request_and_decision(repos, workspace, workflow_service, version_service, engine, approval_service):
    wf = await make_approval_workflow(workflow_service, version_service, workspace, approval_config={"approval_chain": [["mgr-1"]]})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    request = (await approval_service.list_for_execution(execution.id))[0]

    await approval_service.approve_step(request.id, decided_by="mgr-1")

    events = await repos.events.list_for_source("approval", request.id)
    event_types = [e.event_type for e in events]
    assert "approval_requested" in event_types
    assert "approval_decided" in event_types
