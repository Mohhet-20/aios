import asyncio

import pytest

from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.scheduler.scheduler_service import ScheduleService
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import build_default_handler_registry


@pytest.fixture(autouse=True)
async def _seed(repos):
    await seed_node_definitions(repos)


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Sched Co", organization_id="org-1", slug="sched-co"))


@pytest.fixture
def workflow_service(repos):
    return WorkflowService(repos)


@pytest.fixture
def version_service(repos):
    return WorkflowVersionService(repos)


@pytest.fixture
def schedule_service(repos):
    return ScheduleService(repos)


@pytest.fixture
def engine(repos):
    bridges = build_reference_bridge_set()
    handlers = build_default_handler_registry(bridges=bridges)
    return ExecutionEngine(repos, handlers, bridges=bridges, sleep_fn=lambda s: asyncio.sleep(0))


async def make_trivial_workflow(workflow_service, version_service, workspace, *, name="Sched WF"):
    """START -> END, published, ready to be triggered by a schedule."""
    from tests.execution.conftest import publish_graph

    wf = await workflow_service.create_workflow(workspace.id, name=name, owner_id="u1", category="scheduled_job")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[{"source_node_key": "start", "target_node_key": "end"}],
    )
    return wf
