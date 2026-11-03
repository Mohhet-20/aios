import pytest

from eval_platform.agent_workflow.bridges import InMemoryAgentPlatformBridge, InMemoryWorkflowPlatformBridge
from eval_platform.agent_workflow.executors import AgentTargetExecutor, WorkflowTargetExecutor
from eval_platform.agent_workflow.traces import AgentExecutionTrace, WorkflowExecutionTrace
from eval_platform.core.exceptions import EvaluationExecutionError


class _FakeItem:
    def __init__(self, id_):
        self.id = id_


@pytest.mark.asyncio
async def test_in_memory_agent_bridge_round_trip():
    bridge = InMemoryAgentPlatformBridge()
    trace = AgentExecutionTrace(success=True, final_output="42")
    bridge.register("t1", trace)
    fetched = await bridge.get_execution_trace({"trace_id": "t1"})
    assert fetched is trace


@pytest.mark.asyncio
async def test_in_memory_agent_bridge_missing_trace_raises():
    bridge = InMemoryAgentPlatformBridge()
    with pytest.raises(EvaluationExecutionError):
        await bridge.get_execution_trace({"trace_id": "missing"})


@pytest.mark.asyncio
async def test_agent_target_executor_produces_result_and_diagnostics():
    trace = AgentExecutionTrace(
        success=True, final_output="the answer", latency_ms=250.0,
        planned_steps=["a", "b"], executed_steps=["a", "b"],
        tool_calls=[{"selected_correctly": True}],
    )
    bridge = InMemoryAgentPlatformBridge({"t1": trace})
    executor = AgentTargetExecutor(bridge)

    result = await executor.execute({"type": "agent", "ref": {"trace_id": "t1"}}, _FakeItem("item-1"))
    assert result.actual_output == "the answer"
    assert result.success is True
    assert result.latency_ms == 250.0
    assert result.extra_metrics["agent_task_completion"] == 1.0
    assert result.extra_metrics["agent_planning_quality"] == 1.0
    assert result.extra_metrics["agent_tool_selection_quality"] == 1.0


@pytest.mark.asyncio
async def test_agent_target_executor_resolves_ref_from_trace_map():
    trace = AgentExecutionTrace(success=True, final_output="mapped")
    bridge = InMemoryAgentPlatformBridge({"per-item": trace})
    executor = AgentTargetExecutor(bridge)

    result = await executor.execute({"type": "agent", "trace_map": {"item-9": {"trace_id": "per-item"}}}, _FakeItem("item-9"))
    assert result.actual_output == "mapped"


@pytest.mark.asyncio
async def test_agent_target_executor_no_ref_raises():
    executor = AgentTargetExecutor(InMemoryAgentPlatformBridge())
    with pytest.raises(EvaluationExecutionError):
        await executor.execute({"type": "agent"}, _FakeItem("item-1"))


@pytest.mark.asyncio
async def test_workflow_target_executor_produces_result_and_diagnostics():
    trace = WorkflowExecutionTrace(
        success=True, final_output={"result": "ok"}, latency_ms=500.0,
        nodes=[{"status": "succeeded"}, {"status": "succeeded"}],
        parallel_branches=[{"duration_ms": 100}, {"duration_ms": 100}],
    )
    bridge = InMemoryWorkflowPlatformBridge({"w1": trace})
    executor = WorkflowTargetExecutor(bridge)

    result = await executor.execute({"type": "workflow", "ref": {"trace_id": "w1"}}, _FakeItem("item-1"))
    assert result.actual_output == {"result": "ok"}
    assert result.extra_metrics["workflow_execution_success"] == 1.0
    assert result.extra_metrics["workflow_node_reliability"] == 1.0
    assert result.extra_metrics["workflow_parallel_execution_efficiency"] == 1.0
