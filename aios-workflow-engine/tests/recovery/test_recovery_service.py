from datetime import timedelta

import pytest

from tests.execution.conftest import make_engine, publish_graph
from workflow_platform.core.exceptions import NotFoundError, ValidationError
from workflow_platform.database.base import utcnow
from workflow_platform.domain.enums import ExecutionStatus
from workflow_platform.models.checkpoint import CheckpointModel
from workflow_platform.models.execution import ExecutionModel
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.recovery.recovery_service import RecoveryService
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService


@pytest.fixture(autouse=True)
async def _seed(repos):
    await seed_node_definitions(repos)


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Recovery Co", organization_id="org-1", slug="recovery-co"))


async def _make_workflow_and_version(repos, workspace, *, name="Recovery WF"):
    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await wf_service.create_workflow(workspace.id, name=name, owner_id="u1", category="automation")
    version = await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "step1", "node_type": "delay", "name": "Step1", "config": {"seconds": 0}},
            {"node_key": "step2", "node_type": "delay", "name": "Step2", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "step1"},
            {"source_node_key": "step1", "target_node_key": "step2"},
            {"source_node_key": "step2", "target_node_key": "end"},
        ],
    )
    return wf, version


@pytest.mark.asyncio
async def test_restore_from_latest_checkpoint(repos, workspace):
    wf, version = await _make_workflow_and_version(repos, workspace)
    execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, current_node_key="step2",
        context_variables={"stale": True}, triggered_by="u1",
    ))
    await repos.checkpoints.add(CheckpointModel(
        execution_id=execution.id, node_key="step1", sequence_number=1,
        state_snapshot={"context_variables": {"progress": "after_step1"}, "current_node_key": "step2"},
    ))

    recovery = RecoveryService(repos)
    restored = await recovery.restore_from_checkpoint(execution.id)
    assert restored.status == ExecutionStatus.PAUSED.value
    assert restored.context_variables == {"progress": "after_step1"}
    assert restored.current_node_key == "step2"


@pytest.mark.asyncio
async def test_restore_from_specific_sequence_number(repos, workspace):
    wf, version = await _make_workflow_and_version(repos, workspace)
    execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.PAUSED.value, triggered_by="u1",
    ))
    await repos.checkpoints.add(CheckpointModel(
        execution_id=execution.id, node_key="step1", sequence_number=1,
        state_snapshot={"context_variables": {"n": 1}, "current_node_key": "step2"},
    ))
    await repos.checkpoints.add(CheckpointModel(
        execution_id=execution.id, node_key="step2", sequence_number=2,
        state_snapshot={"context_variables": {"n": 2}, "current_node_key": "end"},
    ))

    recovery = RecoveryService(repos)
    restored = await recovery.restore_from_checkpoint(execution.id, sequence_number=1)
    assert restored.context_variables == {"n": 1}
    assert restored.current_node_key == "step2"


@pytest.mark.asyncio
async def test_restore_without_checkpoint_raises(repos, workspace):
    wf, version = await _make_workflow_and_version(repos, workspace)
    execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, triggered_by="u1",
    ))
    recovery = RecoveryService(repos)
    with pytest.raises(NotFoundError):
        await recovery.restore_from_checkpoint(execution.id)


@pytest.mark.asyncio
async def test_restore_rejects_terminal_execution(repos, workspace):
    wf, version = await _make_workflow_and_version(repos, workspace)
    execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.COMPLETED.value, triggered_by="u1",
    ))
    recovery = RecoveryService(repos)
    with pytest.raises(ValidationError):
        await recovery.restore_from_checkpoint(execution.id)


@pytest.mark.asyncio
async def test_recover_stalled_executions_pauses_old_running_ones(repos, workspace):
    wf, version = await _make_workflow_and_version(repos, workspace)

    stale_execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, current_node_key="step2", triggered_by="u1",
    ))
    old_checkpoint_time = utcnow() - timedelta(hours=2)
    checkpoint = await repos.checkpoints.add(CheckpointModel(
        execution_id=stale_execution.id, node_key="step1", sequence_number=1,
        state_snapshot={"context_variables": {"progress": 1}, "current_node_key": "step2"},
    ))
    checkpoint.created_at = old_checkpoint_time
    await repos.checkpoints.update(checkpoint)

    fresh_execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, current_node_key="step1", triggered_by="u1",
    ))
    await repos.checkpoints.add(CheckpointModel(
        execution_id=fresh_execution.id, node_key="start", sequence_number=1,
        state_snapshot={"context_variables": {}, "current_node_key": "step1"},
    ))

    recovery = RecoveryService(repos)
    recovered = await recovery.recover_stalled_executions(stalled_after_seconds=3600)
    recovered_ids = {e.id for e in recovered}
    assert stale_execution.id in recovered_ids
    assert fresh_execution.id not in recovered_ids

    refreshed_stale = await repos.executions.get_or_404(stale_execution.id)
    assert refreshed_stale.status == ExecutionStatus.PAUSED.value
    refreshed_fresh = await repos.executions.get_or_404(fresh_execution.id)
    assert refreshed_fresh.status == ExecutionStatus.RUNNING.value


@pytest.mark.asyncio
async def test_recover_stalled_without_checkpoint_still_pauses(repos, workspace):
    wf, version = await _make_workflow_and_version(repos, workspace)
    execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, triggered_by="u1",
    ))
    execution.started_at = utcnow() - timedelta(hours=2)
    await repos.executions.update(execution)

    recovery = RecoveryService(repos)
    recovered = await recovery.recover_stalled_executions(stalled_after_seconds=3600)
    assert execution.id in {e.id for e in recovered}
    refreshed = await repos.executions.get_or_404(execution.id)
    assert refreshed.status == ExecutionStatus.PAUSED.value


@pytest.mark.asyncio
async def test_full_engine_run_leaves_replayable_checkpoints(repos, workspace):
    wf, version = await _make_workflow_and_version(repos, workspace)
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value

    recovery = RecoveryService(repos)
    checkpoints = await recovery.list_checkpoints(execution.id)
    assert len(checkpoints) == 4  # one after each of start, step1, step2, end
    assert [c.sequence_number for c in checkpoints] == [1, 2, 3, 4]
