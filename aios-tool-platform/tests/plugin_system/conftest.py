import pytest

from tool_platform.marketplace.marketplace_service import MarketplaceService
from tool_platform.models.workspace import WorkspaceModel
from tool_platform.plugin_system.installation_service import PluginInstallationService
from tool_platform.plugin_system.registry_service import PluginRegistryService

_SECRET = "x" * 32


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Plugin Co", organization_id="org-1", slug="plugin-co"))


@pytest.fixture
def registry_service(repos):
    return PluginRegistryService(repos, secret_key=_SECRET)


@pytest.fixture
def marketplace_service(repos):
    return MarketplaceService(repos)


@pytest.fixture
def installation_service(repos):
    return PluginInstallationService(repos, secret_key=_SECRET, require_signature=True)


@pytest.fixture
def installation_service_unsigned_ok(repos):
    return PluginInstallationService(repos, secret_key=_SECRET, require_signature=False)
