import pytest

from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import build_default_handler_registry


@pytest.fixture(autouse=True)
async def _seeded_node_definitions(repos):
    """Every real deployment seeds the node-type registry once at
    bootstrap (see `node_library/registry.seed_node_definitions`) — tests
    do the same so node-definition-driven policy (is_compensable,
    default retry/timeout/backoff) behaves like it would in production
    instead of silently no-op-ing because the table is empty."""
    from workflow_platform.node_library.registry import seed_node_definitions

    await seed_node_definitions(repos)


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Exec Test Co", organization_id="org-1", slug="exec-test-co"))


@pytest.fixture
def workflow_service(repos):
    return WorkflowService(repos)


@pytest.fixture
def version_service(repos):
    return WorkflowVersionService(repos)


async def publish_graph(version_service: WorkflowVersionService, workflow_id: str, *, nodes: list[dict], edges: list[dict], created_by: str = "u1"):
    """Builds a draft version from plain dicts and publishes it, returning
    the published WorkflowVersionModel. `nodes`/`edges` use the same kwarg
    shape as `version_service.add_node`/`add_edge`."""
    draft = await version_service.get_or_create_draft(workflow_id, created_by=created_by)
    for n in nodes:
        await version_service.add_node(draft.id, **n)
    for e in edges:
        await version_service.add_edge(draft.id, **e)
    return await version_service.publish_version(draft.id)


def make_engine(repos, *, ai_core=None, sleep_fn=None, custom_handlers=None, http_client=None, max_recursion_depth=10):
    bridges = build_reference_bridge_set()
    handlers = build_default_handler_registry(bridges=bridges, http_client=http_client, custom_handlers=custom_handlers)
    kwargs = {"ai_core": ai_core, "bridges": bridges, "max_recursion_depth": max_recursion_depth}
    if sleep_fn is not None:
        kwargs["sleep_fn"] = sleep_fn
    return ExecutionEngine(repos, handlers, **kwargs)
