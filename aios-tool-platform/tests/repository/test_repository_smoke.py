"""Not exhaustive per-repository coverage (each service's own test suite
exercises its repositories thoroughly) — just a fast end-to-end sanity
check that every repository is wired into the registry correctly and can
round-trip a row, since a typo in `registry.py` (wrong import, wrong
class) wouldn't otherwise surface until some much later, harder-to-place
test failed."""
import pytest

from tool_platform.models.credential import CredentialModel
from tool_platform.models.execution import ToolExecutionModel
from tool_platform.models.plugin import PluginModel
from tool_platform.models.tool import ToolModel, ToolVersionModel
from tool_platform.models.workspace import WorkspaceModel


@pytest.mark.asyncio
async def test_workspace_roundtrip(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Acme", slug="acme", organization_id="org-1"))
    fetched = await repos.workspaces.get_or_404(ws.id)
    assert fetched.name == "Acme"
    assert await repos.workspaces.list_by_organization("org-1")


@pytest.mark.asyncio
async def test_tool_and_version_roundtrip(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Acme", slug="acme2", organization_id="org-1"))
    tool = await repos.tools.add(ToolModel(
        workspace_id=ws.id, organization_id="org-1", name="GitHub Reader", slug="github-reader",
        owner_id="u1", category="github",
    ))
    version = await repos.tool_versions.add(ToolVersionModel(tool_id=tool.id, version_number=1, created_by="u1"))
    assert await repos.tool_versions.list_for_tool(tool.id) == [version]
    assert await repos.tools.get_by_slug(ws.id, "github-reader") is not None
    assert await repos.tools.list_for_workspace(ws.id, category="github")


@pytest.mark.asyncio
async def test_execution_roundtrip(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Acme", slug="acme3", organization_id="org-1"))
    tool = await repos.tools.add(ToolModel(workspace_id=ws.id, organization_id="org-1", name="T", slug="t", owner_id="u1", category="custom"))
    version = await repos.tool_versions.add(ToolVersionModel(tool_id=tool.id, version_number=1, created_by="u1"))
    execution = await repos.executions.add(ToolExecutionModel(tool_id=tool.id, tool_version_id=version.id, workspace_id=ws.id))
    assert await repos.executions.list_for_tool(tool.id) == [execution]
    assert await repos.executions.count_active_for_tool(tool.id) == 1


@pytest.mark.asyncio
async def test_credential_roundtrip(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Acme", slug="acme4", organization_id="org-1"))
    cred = await repos.credentials.add(CredentialModel(
        workspace_id=ws.id, name="GitHub PAT", credential_type="api_key", encrypted_payload="ciphertext", owner_id="u1",
    ))
    assert await repos.credentials.list_for_workspace(ws.id) == [cred]


@pytest.mark.asyncio
async def test_plugin_roundtrip(repos):
    await repos.plugins.add(PluginModel(name="Slack Connector", slug="slack-connector", author="Acme Inc", category="slack", status="published"))
    assert await repos.plugins.get_by_slug("slack-connector") is not None
    assert await repos.plugins.search(category="slack")
