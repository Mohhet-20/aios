import pytest

from tool_platform.discovery.discovery_service import ToolDiscoveryService
from tool_platform.models.workspace import WorkspaceModel
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Discovery Co", organization_id="org-1", slug="discovery-co"))


@pytest.fixture
def tool_service(repos):
    return ToolService(repos)


@pytest.fixture
def version_service(repos):
    return ToolVersionService(repos)


@pytest.fixture
def discovery_service(repos):
    return ToolDiscoveryService(repos)


async def make_published_tool(tool_service, version_service, workspace, *, name, category, capabilities=None, tags=None, description=None):
    tool = await tool_service.create_tool(
        workspace.id, name=name, owner_id="u1", category=category, organization_id="org-1", tags=tags, description=description,
    )
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.update_draft(draft.id, capabilities=capabilities or [])
    await version_service.publish_version(draft.id)
    return tool
