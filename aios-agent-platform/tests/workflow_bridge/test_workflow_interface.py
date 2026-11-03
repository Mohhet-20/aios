import pytest

from agent_platform.workflow_bridge.workflow_interface import NotIntegratedWorkflowEngine, WorkflowEngineNotIntegratedError


@pytest.mark.asyncio
async def test_start_raises_not_integrated():
    engine = NotIntegratedWorkflowEngine()
    with pytest.raises(WorkflowEngineNotIntegratedError):
        await engine.start("some_workflow", context={})


@pytest.mark.asyncio
async def test_pause_resume_retry_checkpoint_all_raise_not_integrated():
    engine = NotIntegratedWorkflowEngine()
    for coro in (
        engine.pause("exec-1"),
        engine.resume("exec-1"),
        engine.retry("exec-1"),
        engine.checkpoint("exec-1", {"step": 1}),
    ):
        with pytest.raises(WorkflowEngineNotIntegratedError):
            await coro
