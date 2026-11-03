import asyncio

import pytest

from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.approval.approval_service import ApprovalService
from workflow_platform.events.event_bus import EventBus
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import build_default_handler_registry


@pytest.fixture(autouse=True)
async def _seed(repos):
    await seed_node_definitions(repos)


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Approval Co", organization_id="org-1", slug="approval-co"))


@pytest.fixture
def workflow_service(repos):
    return WorkflowService(repos)


@pytest.fixture
def version_service(repos):
    return WorkflowVersionService(repos)


@pytest.fixture
def engine(repos):
    bridges = build_reference_bridge_set()
    handlers = build_default_handler_registry(bridges=bridges)
    eng = ExecutionEngine(repos, handlers, bridges=bridges, sleep_fn=lambda s: asyncio.sleep(0))
    eng.event_bus = EventBus(repos, lock=eng._session_lock)
    eng._extra["event_publisher"] = eng.event_bus.publish
    return eng


@pytest.fixture
def approval_service(repos, engine):
    return ApprovalService(repos, engine=engine, event_bus=engine.event_bus)


async def make_approval_workflow(workflow_service, version_service, workspace, *, approval_config=None, name="Approval WF"):
    from tests.execution.conftest import publish_graph

    wf = await workflow_service.create_workflow(workspace.id, name=name, owner_id="u1", category="approval")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "approve", "node_type": "approval", "name": "Approve", "config": approval_config or {}},
            {"node_key": "after", "node_type": "delay", "name": "After", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "approve"},
            {"source_node_key": "approve", "target_node_key": "after"},
            {"source_node_key": "after", "target_node_key": "end"},
        ],
    )
    return wf
