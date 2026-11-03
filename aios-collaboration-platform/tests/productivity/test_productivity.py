"""Task lifecycle, checklists, bookmarks, and pinned-item reordering
tests."""
from __future__ import annotations

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.core.exceptions import ConflictError, InvalidTransitionError, ValidationError
from collaboration_platform.domain.enums import AssetType, TaskStatus
from collaboration_platform.productivity.bookmark_service import BookmarkService
from collaboration_platform.productivity.checklist_service import ChecklistService
from collaboration_platform.productivity.pinned_service import PinnedItemService
from collaboration_platform.productivity.task_service import TaskService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_ws_and_asset(repos, name="Asset"):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROJECT, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )
    return ws, asset


@pytest.mark.asyncio
async def test_task_lifecycle(repos):
    ws, _ = await _make_ws_and_asset(repos, "task")
    svc = TaskService(repos)
    task = await svc.create_task(ws.id, title="Write launch copy", created_by="user-1")
    assert task.status == TaskStatus.TODO.value

    await svc.assign(task.id, "user-2")
    started = await svc.start(task.id)
    assert started.status == TaskStatus.IN_PROGRESS.value

    completed = await svc.complete(task.id)
    assert completed.status == TaskStatus.DONE.value
    assert completed.completed_at is not None

    with pytest.raises(InvalidTransitionError):
        await svc.cancel(task.id)  # done -> cancelled isn't a legal transition

    reopened = await svc.reopen(task.id)
    assert reopened.status == TaskStatus.IN_PROGRESS.value

    assert len(await svc.list_for_assignee("user-2")) == 1


@pytest.mark.asyncio
async def test_checklist_requires_owner_and_tracks_completion(repos):
    ws, asset = await _make_ws_and_asset(repos, "checklist")
    svc = ChecklistService(repos)
    with pytest.raises(ValidationError):
        await svc.create_checklist(title="Orphan checklist", created_by="user-1")

    checklist = await svc.create_checklist(title="Launch checklist", created_by="user-1", asset_id=asset.id)
    item1 = await svc.add_item(checklist.id, text="Write copy")
    item2 = await svc.add_item(checklist.id, text="Review copy")
    assert item1.position == 0 and item2.position == 1

    toggled = await svc.toggle_item(item1.id)
    assert toggled.is_done is True
    items = await svc.list_items(checklist.id)
    assert sum(1 for i in items if i.is_done) == 1


@pytest.mark.asyncio
async def test_bookmarks(repos):
    ws, asset = await _make_ws_and_asset(repos, "bookmark")
    svc = BookmarkService(repos)
    await svc.add_bookmark("user-1", asset.id, note="revisit before launch")
    with pytest.raises(ConflictError):
        await svc.add_bookmark("user-1", asset.id)
    assert len(await svc.list_for_user("user-1")) == 1
    await svc.remove_bookmark("user-1", asset.id)
    assert len(await svc.list_for_user("user-1")) == 0


@pytest.mark.asyncio
async def test_pinned_items_reorder(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Pin WS", owner_id="user-1")
    asset_svc = CollaborationAssetService(repos)
    assets = [
        await asset_svc.register_asset(workspace_id=ws.id, asset_type=AssetType.REPORT, external_ref_id=f"r{i}", name=f"Report {i}", owner_id="user-1")
        for i in range(3)
    ]
    pin_svc = PinnedItemService(repos)
    for a in assets:
        await pin_svc.pin("user-1", ws.id, a.id)

    with pytest.raises(ConflictError):
        await pin_svc.pin("user-1", ws.id, assets[0].id)

    pinned = await pin_svc.list_for_user_and_workspace("user-1", ws.id)
    assert [p.position for p in pinned] == [0, 1, 2]

    reversed_order = [a.id for a in reversed(assets)]
    reordered = await pin_svc.reorder("user-1", ws.id, reversed_order)
    positions = {p.asset_id: p.position for p in reordered}
    assert positions[assets[2].id] == 0
    assert positions[assets[0].id] == 2
