import pytest

from tool_platform.models.workspace import WorkspaceModel
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService
from tool_platform.tool_execution.engine import ToolExecutionEngine
from tool_platform.tool_execution.registry import ConnectorRegistry, build_default_connector_registry


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Exec Test Co", organization_id="org-1", slug="exec-test-co"))


@pytest.fixture
def tool_service(repos):
    return ToolService(repos)


@pytest.fixture
def version_service(repos):
    return ToolVersionService(repos)


async def make_published_tool(
    tool_service, version_service, workspace, *, name="Test Tool", category="custom", connector_key="echo",
    input_schema=None, output_schema=None, default_max_retries=0, default_timeout_seconds=60,
    default_retry_backoff_seconds=0.01, configuration=None,
):
    tool = await tool_service.create_tool(workspace.id, name=name, owner_id="u1", category=category, organization_id="org-1")
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.update_draft(
        draft.id, connector_key=connector_key, input_schema=input_schema or {}, output_schema=output_schema or {},
        default_max_retries=default_max_retries, default_timeout_seconds=default_timeout_seconds,
        default_retry_backoff_seconds=default_retry_backoff_seconds, configuration=configuration or {},
    )
    published = await version_service.publish_version(draft.id)
    return tool, published


def make_engine(repos, connectors: ConnectorRegistry | None = None, *, vault=None, sleep_fn=None) -> ToolExecutionEngine:
    kwargs = {"vault": vault}
    if sleep_fn is not None:
        kwargs["sleep_fn"] = sleep_fn
    return ToolExecutionEngine(repos, connectors or build_default_connector_registry(), **kwargs)
