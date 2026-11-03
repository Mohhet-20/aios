import pytest

from eval_platform.agent_workflow.analysis import (
    agent_collaboration_quality,
    agent_delegation_quality,
    agent_diagnostics,
    agent_memory_usage_quality,
    agent_planning_quality,
    agent_recovery_quality,
    agent_task_completion,
    agent_tool_selection_quality,
    agent_verification_quality,
    workflow_approval_flow_efficiency,
    workflow_diagnostics,
    workflow_execution_success,
    workflow_node_reliability,
    workflow_parallel_execution_efficiency,
    workflow_recovery_quality,
    workflow_resource_usage_score,
)
from eval_platform.agent_workflow.traces import AgentExecutionTrace, WorkflowExecutionTrace
from eval_platform.core.exceptions import EvaluationExecutionError


def test_agent_task_completion():
    assert agent_task_completion(AgentExecutionTrace(success=True)) == 1.0
    assert agent_task_completion(AgentExecutionTrace(success=False)) == 0.0


def test_agent_planning_quality_requires_both_lists():
    with pytest.raises(EvaluationExecutionError):
        agent_planning_quality(AgentExecutionTrace(success=True))
    trace = AgentExecutionTrace(success=True, planned_steps=["a", "b"], executed_steps=["a", "c"])
    score = agent_planning_quality(trace)
    assert 0.0 < score < 1.0


def test_agent_delegation_and_tool_selection_and_memory():
    trace = AgentExecutionTrace(
        success=True,
        delegated_tasks=[{"completed": True}, {"completed": False}],
        tool_calls=[{"selected_correctly": True}, {"selected_correctly": True}],
        memory_retrievals=[{"relevant": True}, {"relevant": False}, {"relevant": True}],
    )
    assert agent_delegation_quality(trace) == 0.5
    assert agent_tool_selection_quality(trace) == 1.0
    assert round(agent_memory_usage_quality(trace), 4) == round(2 / 3, 4)


def test_agent_recovery_quality_requires_failure_flag():
    with pytest.raises(EvaluationExecutionError):
        agent_recovery_quality(AgentExecutionTrace(success=True, had_failure=False))
    assert agent_recovery_quality(AgentExecutionTrace(success=True, had_failure=True, recovered_from_failure=True)) == 1.0
    assert agent_recovery_quality(AgentExecutionTrace(success=False, had_failure=True, recovered_from_failure=False)) == 0.0


def test_agent_verification_and_collaboration_quality():
    trace = AgentExecutionTrace(
        success=True, verifications=[{"passed": True}, {"passed": True}], collaborators=[{"successful": False}],
    )
    assert agent_verification_quality(trace) == 1.0
    assert agent_collaboration_quality(trace) == 0.0


def test_agent_diagnostics_skips_missing_signals():
    trace = AgentExecutionTrace(success=True)
    results = agent_diagnostics(trace)
    assert results == {"agent_task_completion": 1.0}


def test_workflow_execution_success_and_node_reliability():
    trace = WorkflowExecutionTrace(success=True, nodes=[{"status": "succeeded"}, {"status": "failed"}])
    assert workflow_execution_success(trace) == 1.0
    assert workflow_node_reliability(trace) == 0.5


def test_workflow_recovery_quality_requires_a_retry():
    with pytest.raises(EvaluationExecutionError):
        workflow_recovery_quality(WorkflowExecutionTrace(success=True, nodes=[{"status": "succeeded", "retries": 0}]))
    trace = WorkflowExecutionTrace(success=True, nodes=[{"status": "succeeded", "retries": 1}, {"status": "failed", "retries": 2}])
    assert workflow_recovery_quality(trace) == 0.5


def test_workflow_parallel_execution_efficiency():
    trace = WorkflowExecutionTrace(success=True, parallel_branches=[{"duration_ms": 100}, {"duration_ms": 100}])
    assert workflow_parallel_execution_efficiency(trace) == 1.0
    uneven = WorkflowExecutionTrace(success=True, parallel_branches=[{"duration_ms": 50}, {"duration_ms": 150}])
    assert 0.0 < workflow_parallel_execution_efficiency(uneven) < 1.0


def test_workflow_approval_flow_efficiency_uses_target():
    fast = WorkflowExecutionTrace(success=True, approvals=[1000.0], approval_target_latency_ms=2000.0)
    assert workflow_approval_flow_efficiency(fast) == 1.0
    slow = WorkflowExecutionTrace(success=True, approvals=[10_000.0], approval_target_latency_ms=2000.0)
    assert workflow_approval_flow_efficiency(slow) == 0.2


def test_workflow_resource_usage_score():
    trace = WorkflowExecutionTrace(success=True, resource_usage={"cpu_seconds": 4.0, "budget_cpu_seconds": 2.0})
    assert workflow_resource_usage_score(trace) == 0.5
    with pytest.raises(EvaluationExecutionError):
        workflow_resource_usage_score(WorkflowExecutionTrace(success=True))


def test_workflow_diagnostics_skips_missing_signals():
    trace = WorkflowExecutionTrace(success=True)
    results = workflow_diagnostics(trace)
    assert results == {"workflow_execution_success": 1.0}
