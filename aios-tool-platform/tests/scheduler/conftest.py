import pytest

from tool_platform.models.workspace import WorkspaceModel
from tool_platform.scheduler.schedule_service import ScheduleService
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService
from tool_platform.tool_execution.engine import ToolExecutionEngine
from tool_platform.tool_execution.registry import build_default_connector_registry


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Sched Co", organization_id="org-1", slug="sched-co"))


@pytest.fixture
def tool_service(repos):
    return ToolService(repos)


@pytest.fixture
def version_service(repos):
    return ToolVersionService(repos)


@pytest.fixture
def schedule_service(repos):
    return ScheduleService(repos)


@pytest.fixture
def engine(repos):
    return ToolExecutionEngine(repos, build_default_connector_registry())


async def make_published_tool(tool_service, version_service, workspace, *, name="Sched Tool", connector_key="echo"):
    tool = await tool_service.create_tool(workspace.id, name=name, owner_id="u1", category="custom", organization_id=workspace.organization_id)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.update_draft(draft.id, connector_key=connector_key, default_max_retries=0, default_timeout_seconds=10, default_retry_backoff_seconds=0.01)
    return tool, await version_service.publish_version(draft.id)
