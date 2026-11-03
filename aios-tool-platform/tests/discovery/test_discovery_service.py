import pytest

from tests.discovery.conftest import make_published_tool
from tool_platform.models.execution import ToolExecutionModel


@pytest.mark.asyncio
async def test_search_by_category(discovery_service, tool_service, version_service, workspace):
    await make_published_tool(tool_service, version_service, workspace, name="GitHub Reader", category="github")
    await make_published_tool(tool_service, version_service, workspace, name="Slack Notifier", category="slack")
    results = await discovery_service.search_by_category(workspace.id, "github")
    assert len(results) == 1
    assert results[0].name == "GitHub Reader"


@pytest.mark.asyncio
async def test_search_by_tag(discovery_service, tool_service, version_service, workspace):
    await make_published_tool(tool_service, version_service, workspace, name="A", category="custom", tags=["vcs"])
    await make_published_tool(tool_service, version_service, workspace, name="B", category="custom", tags=["chat"])
    results = await discovery_service.search_by_tag(workspace.id, "vcs")
    assert len(results) == 1
    assert results[0].name == "A"


@pytest.mark.asyncio
async def test_search_by_capability(discovery_service, tool_service, version_service, workspace):
    await make_published_tool(tool_service, version_service, workspace, name="Reader", category="custom", capabilities=["read_file"])
    await make_published_tool(tool_service, version_service, workspace, name="Writer", category="custom", capabilities=["write_file"])
    results = await discovery_service.search_by_capability(workspace.id, "read_file")
    assert len(results) == 1
    assert results[0].name == "Reader"


@pytest.mark.asyncio
async def test_semantic_search_ranks_by_relevance(discovery_service, tool_service, version_service, workspace):
    await make_published_tool(
        tool_service, version_service, workspace, name="GitHub Repo Reader", category="github",
        description="Reads files and issues from a GitHub repository",
    )
    await make_published_tool(
        tool_service, version_service, workspace, name="Weather Lookup", category="custom",
        description="Looks up current weather for a city",
    )
    results = await discovery_service.semantic_search(workspace.id, "github repository files")
    assert len(results) >= 1
    assert results[0].name == "GitHub Repo Reader"


@pytest.mark.asyncio
async def test_semantic_search_no_match_returns_empty(discovery_service, tool_service, version_service, workspace):
    await make_published_tool(tool_service, version_service, workspace, name="A", category="custom", description="nothing relevant")
    results = await discovery_service.semantic_search(workspace.id, "completely unrelated query xyz123")
    assert results == []


@pytest.mark.asyncio
async def test_recently_used_derived_from_executions(discovery_service, tool_service, version_service, workspace, repos):
    tool_a = await make_published_tool(tool_service, version_service, workspace, name="Tool A", category="custom")
    tool_b = await make_published_tool(tool_service, version_service, workspace, name="Tool B", category="custom")

    await repos.executions.add(ToolExecutionModel(tool_id=tool_a.id, tool_version_id=tool_a.current_version_id, workspace_id=workspace.id, triggered_by="u1"))
    await repos.executions.add(ToolExecutionModel(tool_id=tool_b.id, tool_version_id=tool_b.current_version_id, workspace_id=workspace.id, triggered_by="u1"))

    recent = await discovery_service.recently_used("u1")
    assert {t.name for t in recent} == {"Tool A", "Tool B"}


@pytest.mark.asyncio
async def test_recently_used_deduplicates_repeated_tool(discovery_service, tool_service, version_service, workspace, repos):
    tool = await make_published_tool(tool_service, version_service, workspace, name="Repeated Tool", category="custom")
    for _ in range(3):
        await repos.executions.add(ToolExecutionModel(tool_id=tool.id, tool_version_id=tool.current_version_id, workspace_id=workspace.id, triggered_by="u1"))
    recent = await discovery_service.recently_used("u1")
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_favorites_add_list_remove(discovery_service, tool_service, version_service, workspace):
    tool = await make_published_tool(tool_service, version_service, workspace, name="Fav Tool", category="custom")
    await discovery_service.add_favorite(tool.id, "u1")
    favorites = await discovery_service.list_favorites("u1")
    assert len(favorites) == 1
    assert favorites[0].id == tool.id

    await discovery_service.remove_favorite(tool.id, "u1")
    assert await discovery_service.list_favorites("u1") == []


@pytest.mark.asyncio
async def test_add_favorite_is_idempotent(discovery_service, tool_service, version_service, workspace, repos):
    tool = await make_published_tool(tool_service, version_service, workspace, name="Idempotent Fav", category="custom")
    await discovery_service.add_favorite(tool.id, "u1")
    await discovery_service.add_favorite(tool.id, "u1")
    favorites = await repos.tool_favorites.list_for_user("u1")
    assert len(favorites) == 1


@pytest.mark.asyncio
async def test_recommend_prefers_recent_category_and_popularity(discovery_service, tool_service, version_service, workspace, repos):
    used_tool = await make_published_tool(tool_service, version_service, workspace, name="Used GitHub Tool", category="github")
    await repos.executions.add(ToolExecutionModel(tool_id=used_tool.id, tool_version_id=used_tool.current_version_id, workspace_id=workspace.id, triggered_by="u1"))

    await make_published_tool(tool_service, version_service, workspace, name="Another GitHub Tool", category="github")
    other_category_tool = await make_published_tool(tool_service, version_service, workspace, name="Slack Tool", category="slack")
    # Make the other-category tool artificially "popular" workspace-wide via other users.
    for _ in range(5):
        await repos.executions.add(ToolExecutionModel(tool_id=other_category_tool.id, tool_version_id=other_category_tool.current_version_id, workspace_id=workspace.id, triggered_by="u2"))

    recommendations = await discovery_service.recommend(workspace.id, "u1", limit=5)
    rec_names = [t.name for t in recommendations]
    # Same-category match should outrank a merely-more-popular tool in a different category.
    assert rec_names.index("Another GitHub Tool") < rec_names.index("Slack Tool")


@pytest.mark.asyncio
async def test_recommend_excludes_already_favorited(discovery_service, tool_service, version_service, workspace):
    tool = await make_published_tool(tool_service, version_service, workspace, name="Already Fav", category="custom")
    await discovery_service.add_favorite(tool.id, "u1")
    recommendations = await discovery_service.recommend(workspace.id, "u1")
    assert tool.id not in {t.id for t in recommendations}
