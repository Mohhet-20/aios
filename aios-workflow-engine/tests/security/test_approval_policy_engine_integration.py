"""Verifies ApprovalPolicyService (Task 94) is actually wired into the
Execution Engine's APPROVAL node handler — a CRITICAL-sensitivity
approval node with too short a chain fails the node (and therefore the
execution) rather than silently accepting an under-governed request."""
import asyncio

import pytest

from tests.execution.conftest import publish_graph
from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.domain.enums import ExecutionStatus
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.security.policy_service import ApprovalPolicyService
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import build_default_handler_registry


@pytest.fixture(autouse=True)
async def _seed(repos):
    await seed_node_definitions(repos)


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Policy Engine Co", organization_id="org-1", slug="policy-engine-co"))


def _engine_with_policy(repos):
    bridges = build_reference_bridge_set()
    handlers = build_default_handler_registry(bridges=bridges)
    return ExecutionEngine(repos, handlers, bridges=bridges, sleep_fn=lambda s: asyncio.sleep(0), approval_policy=ApprovalPolicyService())


async def _approval_workflow(workflow_service, version_service, workspace, *, approval_chain, sensitivity_level):
    wf = await workflow_service.create_workflow(workspace.id, name="Critical Approval WF", owner_id="u1", category="approval")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "approve", "node_type": "approval", "name": "Approve", "config": {
                "approval_chain": approval_chain, "sensitivity_level": sensitivity_level,
            }},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "approve"},
            {"source_node_key": "approve", "target_node_key": "end"},
        ],
    )
    return wf


@pytest.mark.asyncio
async def test_undersized_critical_chain_is_rejected(repos, workspace):
    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await _approval_workflow(wf_service, version_service, workspace, approval_chain=[["mgr-1"]], sensitivity_level="critical")

    engine = _engine_with_policy(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status in (ExecutionStatus.FAILED.value, ExecutionStatus.COMPENSATED.value)


@pytest.mark.asyncio
async def test_properly_sized_critical_chain_pauses_normally(repos, workspace):
    wf_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await _approval_workflow(
        wf_service, version_service, workspace,
        approval_chain=[["mgr-1"], ["fin-1"], ["cfo-1"]], sensitivity_level="critical",
    )

    engine = _engine_with_policy(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.WAITING_APPROVAL.value
