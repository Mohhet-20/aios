import pytest

from tool_platform.ai_planning.planning_service import ToolPlanningService
from tool_platform.discovery.discovery_service import ToolDiscoveryService
from tool_platform.models.workspace import WorkspaceModel
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Planning Co", organization_id="org-1", slug="planning-co"))


@pytest.fixture
def tool_service(repos):
    return ToolService(repos)


@pytest.fixture
def version_service(repos):
    return ToolVersionService(repos)


@pytest.fixture
def planning_service(repos):
    return ToolPlanningService(repos, ToolDiscoveryService(repos))


async def make_published_tool(
    tool_service, version_service, workspace, *, name, category, capabilities,
    input_schema=None, description=None, tags=None, connector_key="echo",
):
    tool = await tool_service.create_tool(
        workspace.id, name=name, owner_id="u1", category=category,
        organization_id=workspace.organization_id, description=description, tags=tags or [],
    )
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    draft = await version_service.update_draft(
        draft.id, capabilities=capabilities, input_schema=input_schema or {},
        connector_key=connector_key,
    )
    await version_service.publish_version(draft.id)
    return await tool_service.get_tool(tool.id)
