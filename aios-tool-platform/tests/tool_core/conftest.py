import pytest

from tool_platform.models.workspace import WorkspaceModel
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Tool Core Co", organization_id="org-1", slug="tool-core-co"))


@pytest.fixture
def tool_service(repos):
    return ToolService(repos)


@pytest.fixture
def version_service(repos):
    return ToolVersionService(repos)
