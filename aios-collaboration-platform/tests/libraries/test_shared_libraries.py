"""Shared library publish/unpublish, visibility, favorites, and a
genuine concurrent-install stress test for the atomic install-count
increment (matches the established methodology: real `asyncio.gather`
concurrency through independent `session_scope()`s, not the
rollback-isolated `repos` fixture, so writes actually persist and
commit before the next concurrent caller reads)."""
from __future__ import annotations

import asyncio

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.core.exceptions import ConflictError
from collaboration_platform.database.session import session_scope
from collaboration_platform.domain.enums import AssetType, LibraryVisibility
from collaboration_platform.libraries.library_service import LibraryService
from collaboration_platform.repositories.registry import RepositoryRegistry
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_asset(repos, name="Asset"):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    return await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.TEMPLATE, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )


@pytest.mark.asyncio
async def test_publish_unpublish_and_visibility(repos):
    asset = await _make_asset(repos, "publish")
    svc = LibraryService(repos)
    entry = await svc.publish(asset.id, library_type="prompt", published_by="user-1")
    assert entry.visibility == LibraryVisibility.PRIVATE.value

    with pytest.raises(ConflictError):
        await svc.publish(asset.id, library_type="prompt", published_by="user-1")

    updated = await svc.update_visibility(entry.id, LibraryVisibility.PUBLIC)
    assert updated.visibility == LibraryVisibility.PUBLIC.value
    assert len(await svc.list_published(visibility=LibraryVisibility.PUBLIC)) == 1

    unpublished = await svc.unpublish(entry.id)
    assert unpublished.unpublished_at is not None
    assert len(await svc.list_published()) == 0


@pytest.mark.asyncio
async def test_favorite_unfavorite(repos):
    asset = await _make_asset(repos, "favorite")
    svc = LibraryService(repos)
    entry = await svc.publish(asset.id, library_type="agent", published_by="user-1")

    await svc.favorite("user-2", entry.id)
    with pytest.raises(ConflictError):
        await svc.favorite("user-2", entry.id)
    assert len(await svc.list_favorites_for_user("user-2")) == 1

    await svc.unfavorite("user-2", entry.id)
    assert len(await svc.list_favorites_for_user("user-2")) == 0


@pytest.mark.asyncio
async def test_concurrent_installs_never_undercount():
    """20 concurrent `record_install` calls against independent DB
    sessions/connections — the atomic UPDATE must land every increment,
    unlike a naive read-count-then-write-count pattern which would lose
    increments under real concurrency."""
    outcome: dict = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        asset = await _make_asset(repos, "concurrent-install")
        entry = await LibraryService(repos).publish(asset.id, library_type="workflow_template", published_by="user-1")
        outcome["library_asset_id"] = entry.id

    library_asset_id = outcome["library_asset_id"]

    async def install_once() -> None:
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            await LibraryService(repos).record_install(library_asset_id)

    results = await asyncio.gather(*[install_once() for _ in range(20)], return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]
    assert not failures, f"unexpected exceptions during concurrent installs: {failures}"

    final_count = {}
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        entry = await repos.library_assets.get_or_404(library_asset_id)
        final_count["install_count"] = entry.install_count

    assert final_count["install_count"] == 20, f"expected 20 installs, got {final_count['install_count']}"
