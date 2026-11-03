import pytest

from prompt_platform.core.exceptions import ValidationError
from prompt_platform.models.observability import PromptExecutionLogModel
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_registry.library_service import PromptLibraryService


async def _seed_prompt(repos, name, slug, **kw):
    ws = kw.get("ws")
    if ws is None:
        ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws-" + slug, organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj-" + slug))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name=name, slug=slug, owner_id="u1"))
    return ws, prompt


@pytest.mark.asyncio
async def test_search_by_query_matches_name(repos):
    svc = PromptLibraryService(repos)
    ws, p1 = await _seed_prompt(repos, "Customer Support Greeting", "greeting")
    _, p2 = await _seed_prompt(repos, "Sales Pitch", "pitch", ws=ws)

    page = await svc.search(ws.id, query="greeting")
    names = [p.name for p in page.items]
    assert "Customer Support Greeting" in names
    assert "Sales Pitch" not in names


@pytest.mark.asyncio
async def test_search_sorts_by_name(repos):
    svc = PromptLibraryService(repos)
    ws, _ = await _seed_prompt(repos, "Zebra", "zebra")
    await _seed_prompt(repos, "Apple", "apple", ws=ws)

    page = await svc.search(ws.id, sort="name")
    assert [p.name for p in page.items][:2] == ["Apple", "Zebra"]


@pytest.mark.asyncio
async def test_favorites_add_list_remove(repos):
    svc = PromptLibraryService(repos)
    ws, prompt = await _seed_prompt(repos, "Fav Me", "fav-me")

    await svc.add_favorite("user1", prompt.id)
    favs = await svc.list_favorites("user1")
    assert prompt.id in [p.id for p in favs]

    await svc.remove_favorite("user1", prompt.id)
    favs_after = await svc.list_favorites("user1")
    assert prompt.id not in [p.id for p in favs_after]


@pytest.mark.asyncio
async def test_archive_and_unarchive(repos):
    svc = PromptLibraryService(repos)
    ws, prompt = await _seed_prompt(repos, "Archivable", "archivable")

    archived = await svc.archive(prompt.id)
    assert archived.status == "archived"
    restored = await svc.unarchive(prompt.id)
    assert restored.status == "active"


@pytest.mark.asyncio
async def test_tagging_updates_cache_and_link_table(repos):
    svc = PromptLibraryService(repos)
    ws, prompt = await _seed_prompt(repos, "Taggable", "taggable")

    await svc.tag_prompt(prompt.id, "customer-support")
    tags = await repos.tags.tags_for_prompt(prompt.id)
    assert "customer-support" in [t.name for t in tags]

    refreshed = await repos.prompts.get(prompt.id)
    assert "customer-support" in refreshed.tags_cache

    await svc.untag_prompt(prompt.id, "customer-support")
    refreshed2 = await repos.prompts.get(prompt.id)
    assert "customer-support" not in refreshed2.tags_cache


@pytest.mark.asyncio
async def test_collections_add_remove_and_duplicate_guard(repos):
    svc = PromptLibraryService(repos)
    ws, prompt = await _seed_prompt(repos, "Collectible", "collectible")
    collection = await svc.create_collection(ws.id, "Q3 Prompts", "u1")

    await svc.add_to_collection(collection.id, prompt.id)
    prompts = await svc.list_collection_prompts(collection.id)
    assert prompt.id in [p.id for p in prompts]

    with pytest.raises(ValidationError):
        await svc.add_to_collection(collection.id, prompt.id)

    await svc.remove_from_collection(collection.id, prompt.id)
    prompts_after = await svc.list_collection_prompts(collection.id)
    assert prompt.id not in [p.id for p in prompts_after]


@pytest.mark.asyncio
async def test_recently_used_and_most_used_derived_from_execution_logs(repos):
    svc = PromptLibraryService(repos)
    ws, p1 = await _seed_prompt(repos, "Popular", "popular")
    _, p2 = await _seed_prompt(repos, "Rare", "rare", ws=ws)
    version = await repos.versions.add(PromptVersionModel(prompt_id=p1.id, version_number=1, user_template="hi"))

    for _ in range(3):
        await repos.execution_logs.add(PromptExecutionLogModel(prompt_id=p1.id, version_id=version.id, source="test"))
    await repos.execution_logs.add(PromptExecutionLogModel(prompt_id=p2.id, version_id=version.id, source="test"))

    most_used = await svc.list_most_used(ws.id, limit=5)
    assert most_used[0][0].id == p1.id
    assert most_used[0][1] == 3

    recent = await svc.list_recently_used(ws.id, limit=5)
    assert recent[0].id in (p1.id, p2.id)


@pytest.mark.asyncio
async def test_category_create_and_list(repos):
    svc = PromptLibraryService(repos)
    await svc.create_category("Support", "support")
    categories = await svc.list_categories()
    assert any(c.slug == "support" for c in categories)
