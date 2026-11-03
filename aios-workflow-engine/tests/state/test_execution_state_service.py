
import pytest

from tests.execution.conftest import make_engine, publish_graph
from workflow_platform.domain.enums import ExecutionStatus
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.state.execution_state_service import ExecutionStateService
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService


@pytest.fixture(autouse=True)
async def _seed(repos):
    await seed_node_definitions(repos)


@pytest.mark.asyncio
async def test_state_snapshot_and_metadata_reflect_completed_run(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="State Co", organization_id="org-1", slug="state-co"))
    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await wf_service.create_workflow(ws.id, name="State WF", owner_id="u1", category="automation")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "delay", "node_type": "delay", "name": "Delay", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "delay"},
            {"source_node_key": "delay", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1", input_variables={"x": 1})
    assert execution.status == ExecutionStatus.COMPLETED.value

    state_service = ExecutionStateService(repos)
    snapshot = await state_service.get_state_snapshot(execution.id)
    assert snapshot["status"] == ExecutionStatus.COMPLETED.value
    assert snapshot["context_variables"]["x"] == 1
    assert snapshot["latest_checkpoint_sequence"] is not None

    metadata = await state_service.get_execution_metadata(execution.id)
    assert metadata["node_execution_count"] == 3
    assert metadata["succeeded_node_count"] == 3
    assert metadata["failed_node_count"] == 0
    assert metadata["duration_ms"] is not None
    assert metadata["duration_ms"] >= 0
