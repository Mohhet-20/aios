import pytest

from tool_platform.core.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from tool_platform.core.pagination import PaginationParams
from tool_platform.domain.enums import ToolStatus


async def _make_tool(tool_service, workspace, *, name="GitHub Reader", category="github"):
    return await tool_service.create_tool(
        workspace.id, name=name, owner_id="u1", category=category, organization_id="org-1",
    )


@pytest.mark.asyncio
async def test_create_tool_auto_slugs(tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    assert tool.slug == "github-reader"
    assert tool.status == ToolStatus.DRAFT.value


@pytest.mark.asyncio
async def test_create_tool_duplicate_slug_rejected(tool_service, workspace):
    await _make_tool(tool_service, workspace)
    with pytest.raises(ValidationError):
        await _make_tool(tool_service, workspace)


@pytest.mark.asyncio
async def test_get_tool_not_found(tool_service):
    with pytest.raises(NotFoundError):
        await tool_service.get_tool("nope")


@pytest.mark.asyncio
async def test_list_and_search_tools(tool_service, workspace):
    await _make_tool(tool_service, workspace, name="GitHub Reader", category="github")
    await _make_tool(tool_service, workspace, name="Slack Notifier", category="slack")

    page = await tool_service.list_tools(workspace.id, PaginationParams(page=1, page_size=10))
    assert page.total == 2

    filtered = await tool_service.list_tools(workspace.id, PaginationParams(page=1, page_size=10), category="slack")
    assert filtered.total == 1

    found = await tool_service.search_tools(workspace.id, "github")
    assert len(found) == 1
    assert found[0].name == "GitHub Reader"


@pytest.mark.asyncio
async def test_update_tool_rejects_unknown_field(tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    with pytest.raises(ValidationError):
        await tool_service.update_tool(tool.id, status="published")


@pytest.mark.asyncio
async def test_update_tool_allowed_fields(tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    updated = await tool_service.update_tool(tool.id, description="Reads GitHub repos", tags=["vcs", "read-only"])
    assert updated.description == "Reads GitHub repos"
    assert updated.tags == ["vcs", "read-only"]


@pytest.mark.asyncio
async def test_delete_tool_soft_deletes(tool_service, workspace, repos):
    tool = await _make_tool(tool_service, workspace)
    await tool_service.delete_tool(tool.id)
    with pytest.raises(NotFoundError):
        await tool_service.get_tool(tool.id)
    raw = await repos.tools.get(tool.id, include_deleted=True)
    assert raw.is_deleted is True


@pytest.mark.asyncio
async def test_publish_flips_status_and_sets_version(tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    published = await tool_service.publish(tool.id, "v-1")
    assert published.status == ToolStatus.PUBLISHED.value
    assert published.current_version_id == "v-1"


@pytest.mark.asyncio
async def test_full_lifecycle_deprecate_disable_enable(tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    await tool_service.publish(tool.id, "v-1")
    deprecated = await tool_service.deprecate(tool.id)
    assert deprecated.status == ToolStatus.DEPRECATED.value
    disabled = await tool_service.disable(tool.id)
    assert disabled.status == ToolStatus.DISABLED.value
    enabled = await tool_service.enable(tool.id)
    assert enabled.status == ToolStatus.PUBLISHED.value


@pytest.mark.asyncio
async def test_draft_cannot_deprecate(tool_service, workspace):
    tool = await _make_tool(tool_service, workspace)
    with pytest.raises(InvalidTransitionError):
        await tool_service.deprecate(tool.id)
