"""End-to-end: an EvaluationRun scoring an agent target through the
real EvaluationRunService + AgentTargetExecutor + InMemoryAgentPlatformBridge,
proving agent diagnostics genuinely flow into EvaluationItemResultModel
and the run's aggregate metric_summary — not just unit-tested in isolation."""
import pytest

from eval_platform.agent_workflow.bridges import InMemoryAgentPlatformBridge
from eval_platform.agent_workflow.executors import AgentTargetExecutor
from eval_platform.agent_workflow.traces import AgentExecutionTrace
from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.evaluation_core.version_service import EvaluationVersionService
from eval_platform.execution.evaluation_run_service import EvaluationRunService
from eval_platform.models.workspace import WorkspaceModel


@pytest.mark.asyncio
async def test_agent_evaluation_run_end_to_end(repos):
    workspace = await repos.workspaces.add(WorkspaceModel(name="Agent Eval Co", organization_id="org-1", slug="agent-eval-co"))

    dataset_service = DatasetService(repos)
    dataset_version_service = DatasetVersionService(repos)
    dataset = await dataset_service.create_dataset(workspace.id, name="Agent Tasks", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
    await dataset_version_service.add_items(draft.id, [
        {"input_data": {"task": "book a flight"}, "expected_output": "booked"},
    ])
    published = await dataset_version_service.publish_version(draft.id)
    items = await dataset_version_service.list_items(published.id)
    item = items[0]

    bridge = InMemoryAgentPlatformBridge()
    bridge.register("trace-1", AgentExecutionTrace(
        success=True, final_output="booked", latency_ms=300.0,
        planned_steps=["search flights", "book flight"], executed_steps=["search flights", "book flight"],
        tool_calls=[{"selected_correctly": True}],
    ))

    evaluation_service = EvaluationService(repos)
    evaluation_version_service = EvaluationVersionService(repos)
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="Agent Task Eval", owner_id="u1", category="agent", organization_id="org-1")
    eval_draft = await evaluation_version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await evaluation_version_service.update_draft(
        eval_draft.id, dataset_id=dataset.id, metric_keys=["accuracy", "task_success_rate"], pass_threshold=0.5,
        target_config={"type": "agent", "trace_map": {item.id: {"trace_id": "trace-1"}}},
    )
    await evaluation_version_service.publish_version(eval_draft.id)
    evaluation = await evaluation_service.get_evaluation(evaluation.id)

    run_service = EvaluationRunService(repos)
    run = await run_service.start_run(evaluation.id, triggered_by="u1")
    completed = await run_service.execute_run(run.id, AgentTargetExecutor(bridge))

    assert completed.status == "succeeded"
    assert completed.passed_count == 1
    assert completed.metric_summary["accuracy"] == 1.0
    assert completed.metric_summary["task_success_rate"] == 1.0
    assert completed.metric_summary["agent_planning_quality"] == 1.0
    assert completed.metric_summary["agent_tool_selection_quality"] == 1.0

    results = await run_service.list_item_results(run.id)
    assert results[0].metric_results["agent_task_completion"] == 1.0
