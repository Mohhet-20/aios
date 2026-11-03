"""Lexical/tag/metadata search, semantic-search fallback, recent
items (LRU trimming), and saved search tests."""
from __future__ import annotations

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.config.settings import Settings
from collaboration_platform.core.exceptions import QuotaExceededError
from collaboration_platform.domain.enums import AssetType
from collaboration_platform.projects.tag_service import TagService
from collaboration_platform.search.recent_items_service import RecentItemsService
from collaboration_platform.search.saved_search_service import SavedSearchService
from collaboration_platform.search.search_service import SearchService
from collaboration_platform.workspace.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_lexical_search_matches_name_and_description(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Search WS", owner_id="user-1")
    asset_svc = CollaborationAssetService(repos)
    await asset_svc.register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROMPT, external_ref_id="p1", name="Customer Onboarding Prompt",
        owner_id="user-1", description="Welcomes new customers",
    )
    await asset_svc.register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROMPT, external_ref_id="p2", name="Refund Policy",
        owner_id="user-1", description="Handles refund questions",
    )

    search_svc = SearchService(repos)
    by_name = await search_svc.search("onboarding", workspace_id=ws.id)
    assert len(by_name) == 1 and by_name[0].name == "Customer Onboarding Prompt"

    by_description = await search_svc.search("refund", workspace_id=ws.id)
    assert len(by_description) == 1 and by_description[0].name == "Refund Policy"

    no_match = await search_svc.search("nonexistent-term", workspace_id=ws.id)
    assert no_match == []


@pytest.mark.asyncio
async def test_semantic_search_falls_back_without_provider(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Semantic WS", owner_id="user-1")
    await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.AGENT, external_ref_id="a1", name="Support Agent", owner_id="user-1",
    )
    search_svc = SearchService(repos)
    results = await search_svc.search("support", workspace_id=ws.id, semantic=True)
    assert len(results) == 1  # NullSemanticSearchProvider passes lexical results through unchanged


@pytest.mark.asyncio
async def test_tag_and_metadata_search(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Tag WS", owner_id="user-1")
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.DASHBOARD, external_ref_id="d1", name="Sales Dashboard", owner_id="user-1",
    )
    tag = await TagService(repos).create_tag(ws.id, name="finance")
    await TagService(repos).tag_asset(asset.id, tag.id)

    search_svc = SearchService(repos)
    by_tag = await search_svc.search_by_tag(ws.id, "finance")
    assert len(by_tag) == 1 and by_tag[0].id == asset.id

    asset.asset_metadata = {"region": "us-east"}
    await repos.assets.update(asset)
    by_meta = await search_svc.search_by_metadata(ws.id, {"region": "us-east"})
    assert len(by_meta) == 1
    no_meta_match = await search_svc.search_by_metadata(ws.id, {"region": "eu-west"})
    assert no_meta_match == []


@pytest.mark.asyncio
async def test_recent_items_lru_trimming(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Recent WS", owner_id="user-1")
    asset_svc = CollaborationAssetService(repos)
    settings = Settings(secret_key="x" * 32, recent_items_per_user_limit=2)
    recent_svc = RecentItemsService(repos, settings=settings)

    assets = []
    for i in range(4):
        a = await asset_svc.register_asset(
            workspace_id=ws.id, asset_type=AssetType.DOCUMENT, external_ref_id=f"doc-{i}", name=f"Doc {i}", owner_id="user-1"
        )
        assets.append(a)
        await recent_svc.track_view("user-1", a.id)

    recent = await recent_svc.list_recent("user-1")
    assert len(recent) == 2
    # most recently viewed two should be the last two tracked
    viewed_asset_ids = {r.asset_id for r in recent}
    assert viewed_asset_ids == {assets[-1].id, assets[-2].id}


@pytest.mark.asyncio
async def test_saved_search_quota(repos):
    settings = Settings(secret_key="x" * 32, saved_search_limit_per_user=2)
    svc = SavedSearchService(repos, settings=settings)
    await svc.create("user-1", name="Search 1", query={"q": "a"})
    await svc.create("user-1", name="Search 2", query={"q": "b"})
    with pytest.raises(QuotaExceededError):
        await svc.create("user-1", name="Search 3", query={"q": "c"})
    assert len(await svc.list_for_user("user-1")) == 2
