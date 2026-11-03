import pytest

from quality_platform.core.exceptions import InvalidTransitionError, WorkflowValidationError
from quality_platform.validation.workflow_validation_service import WorkflowValidationRunService

pytestmark = pytest.mark.asyncio


async def test_start_and_finish_run_all_checks_pass(repos):
    svc = WorkflowValidationRunService(repos)
    run = await svc.request_run("t1", workflow_ref="wf:1")
    assert run.status == "queued"
    await svc.start("t1", run.id)
    await svc.record_check("t1", run.id, check="logic", passed=True)
    await svc.record_check("t1", run.id, check="retries", passed=True)
    finished = await svc.finish_run("t1", run.id)
    assert finished.status == "completed"
    assert finished.result["all_passed"] is True
    assert finished.result["total_checks"] == 2


async def test_finish_run_reports_failed_checks(repos):
    svc = WorkflowValidationRunService(repos)
    run = await svc.request_run("t1", workflow_ref="wf:2")
    await svc.start("t1", run.id)
    await svc.record_check("t1", run.id, check="timeout_handling", passed=True)
    await svc.record_check("t1", run.id, check="approval_chains", passed=False, details="no approver configured")
    finished = await svc.finish_run("t1", run.id)
    assert finished.status == "completed"
    assert finished.result["all_passed"] is False
    assert finished.result["failed_checks"] == ["approval_chains"]


async def test_record_check_rejects_unsupported_check(repos):
    svc = WorkflowValidationRunService(repos)
    run = await svc.request_run("t1", workflow_ref="wf:3")
    await svc.start("t1", run.id)
    with pytest.raises(WorkflowValidationError):
        await svc.record_check("t1", run.id, check="not-a-check", passed=True)


async def test_cannot_finish_without_start(repos):
    svc = WorkflowValidationRunService(repos)
    run = await svc.request_run("t1", workflow_ref="wf:4")
    with pytest.raises(InvalidTransitionError):
        await svc.finish_run("t1", run.id)


async def test_fail_run(repos):
    svc = WorkflowValidationRunService(repos)
    run = await svc.request_run("t1", workflow_ref="wf:5")
    await svc.start("t1", run.id)
    failed = await svc.fail("t1", run.id, error="workflow engine unreachable")
    assert failed.status == "failed"
