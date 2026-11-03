import pytest

from tool_platform.core.exceptions import ValidationError


async def _make_tool(tool_service, workspace, *, name="GitHub Reader", category="github"):
    return await tool_service.create_tool(workspace.id, name=name, owner_id="u1", category=category, organization_id="org-1")


@pytest.mark.asyncio
async def test_get_or_create_draft_creates_first_version(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    assert draft.version_number == 1
    assert draft.status == "draft"


@pytest.mark.asyncio
async def test_get_or_create_draft_is_idempotent(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    first = await version_service.get_or_create_draft(tool.id, created_by="u1")
    second = await version_service.get_or_create_draft(tool.id, created_by="u1")
    assert first.id == second.id


@pytest.mark.asyncio
async def test_update_draft_rejects_unknown_field(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    with pytest.raises(ValidationError):
        await version_service.update_draft(draft.id, status="published")


@pytest.mark.asyncio
async def test_update_draft_sets_schema_and_capabilities(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    updated = await version_service.update_draft(
        draft.id, capabilities=["read_file"], input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        connector_key="github",
    )
    assert updated.capabilities == ["read_file"]
    assert updated.connector_key == "github"


@pytest.mark.asyncio
async def test_publish_rejects_invalid_json_schema(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.update_draft(draft.id, input_schema={"type": "not-a-real-type"})
    with pytest.raises(ValidationError):
        await version_service.publish_version(draft.id)


@pytest.mark.asyncio
async def test_publish_activates_tool(version_service, tool_service, workspace, repos):
    tool = await _make_tool(tool_service, workspace)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.update_draft(draft.id, input_schema={"type": "object"}, connector_key="github")
    published = await version_service.publish_version(draft.id)
    assert published.status == "published"

    refreshed_tool = await repos.tools.get_or_404(tool.id)
    assert refreshed_tool.status == "published"
    assert refreshed_tool.current_version_id == published.id


@pytest.mark.asyncio
async def test_cannot_edit_published_version(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.publish_version(draft.id)
    with pytest.raises(ValidationError):
        await version_service.update_draft(draft.id, capabilities=["x"])


@pytest.mark.asyncio
async def test_new_draft_after_publish_seeds_from_published_contract(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    draft1 = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.update_draft(draft1.id, capabilities=["read_file"], connector_key="github")
    await version_service.publish_version(draft1.id)

    draft2 = await version_service.get_or_create_draft(tool.id, created_by="u1")
    assert draft2.version_number == 2
    assert draft2.capabilities == ["read_file"]
    assert draft2.connector_key == "github"


@pytest.mark.asyncio
async def test_deprecate_version_requires_published(version_service, tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    with pytest.raises(ValidationError):
        await version_service.deprecate_version(draft.id)
    await version_service.publish_version(draft.id)
    deprecated = await version_service.deprecate_version(draft.id)
    assert deprecated.status == "deprecated"
