"""Presence, edit-session quota, conflict detection/resolution, and
sync/CAS guard tests."""
from __future__ import annotations

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.config.settings import Settings
from collaboration_platform.core.exceptions import EditConflictError, QuotaExceededError, StaleWriteError
from collaboration_platform.domain.enums import AssetType, ConflictResolutionStrategy
from collaboration_platform.realtime.conflict_service import ConflictService
from collaboration_platform.realtime.edit_session_service import EditSessionService
from collaboration_platform.realtime.presence_service import PresenceService
from collaboration_platform.realtime.sync_service import SyncService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_asset(repos, name="Asset"):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    return await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.DOCUMENT, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )


@pytest.mark.asyncio
async def test_presence_join_heartbeat_leave(repos):
    asset = await _make_asset(repos, "presence")
    svc = PresenceService(repos)
    await svc.join(asset.id, "user-1", connection_id="conn-1", cursor_position={"line": 1})
    await svc.join(asset.id, "user-2", connection_id="conn-2")
    assert len(await svc.list_active(asset.id)) == 2

    await svc.update_cursor("conn-1", {"line": 5})
    await svc.heartbeat("conn-2")
    await svc.leave("conn-1")
    active = await svc.list_active(asset.id)
    assert len(active) == 1
    assert active[0].user_id == "user-2"


@pytest.mark.asyncio
async def test_edit_session_quota_enforced(repos):
    asset = await _make_asset(repos, "quota")
    settings = Settings(secret_key="x" * 32, max_concurrent_editors_per_asset=2)
    svc = EditSessionService(repos, settings=settings)
    await svc.start_session(asset.id, "user-1")
    await svc.start_session(asset.id, "user-2")
    with pytest.raises(QuotaExceededError):
        await svc.start_session(asset.id, "user-3")


@pytest.mark.asyncio
async def test_conflict_detection_and_resolution(repos):
    asset = await _make_asset(repos, "conflict")
    edit_svc = EditSessionService(repos)
    s1 = await edit_svc.start_session(asset.id, "user-1", base_version_id="v1")
    s2 = await edit_svc.start_session(asset.id, "user-2", base_version_id="v2")

    conflict_svc = ConflictService(repos)
    conflicts = await conflict_svc.detect_conflicts(asset.id)
    assert len(conflicts) == 1
    assert {conflicts[0].session_a_id, conflicts[0].session_b_id} == {s1.id, s2.id}

    # calling detect again shouldn't duplicate the still-unresolved conflict
    again = await conflict_svc.detect_conflicts(asset.id)
    assert len(again) == 0

    resolved = await conflict_svc.resolve(
        conflicts[0].id, strategy=ConflictResolutionStrategy.MANUAL, resolved_by="user-1", notes="merged manually"
    )
    assert resolved.resolved_at is not None
    with pytest.raises(EditConflictError):
        await conflict_svc.resolve(conflicts[0].id, strategy=ConflictResolutionStrategy.MANUAL, resolved_by="user-1")


@pytest.mark.asyncio
async def test_sync_service_stale_write_guard(repos):
    asset = await _make_asset(repos, "sync")
    sync_svc = SyncService(repos)
    # asset has no current_version_id yet, so None is accepted
    await sync_svc.assert_not_stale(asset.id, None)

    asset.current_version_id = "version-abc"
    await repos.assets.update(asset)

    with pytest.raises(StaleWriteError):
        await sync_svc.assert_not_stale(asset.id, "some-other-version")

    # now matches -> no error
    await sync_svc.assert_not_stale(asset.id, "version-abc")


@pytest.mark.asyncio
async def test_resume_offline_session_reports_staleness(repos):
    asset = await _make_asset(repos, "offline")
    edit_svc = EditSessionService(repos)
    # base_version_id=None matches the asset's freshly-created current_version_id (also None)
    session = await edit_svc.start_session(asset.id, "user-1", base_version_id=None)

    sync_svc = SyncService(repos)
    result = await sync_svc.resume_offline_session(session.id)
    assert result["is_stale"] is False

    asset.current_version_id = "v2"
    await repos.assets.update(asset)
    result = await sync_svc.resume_offline_session(session.id)
    assert result["is_stale"] is True
