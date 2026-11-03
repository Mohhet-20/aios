"""Permission resolution (asset override > workspace grant >
membership), share links, external shares, audit log, and retention
sweep tests."""
from __future__ import annotations

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.core.exceptions import (
    ExternalSharingDisabledError,
    PermissionDeniedError,
    ShareLinkExpiredError,
    ShareLinkRevokedError,
)
from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import AssetType, PrincipalType, SharePermission, WorkspaceRole
from collaboration_platform.governance.audit_service import AuditService
from collaboration_platform.governance.permission_service import PermissionService
from collaboration_platform.governance.retention_service import RetentionService
from collaboration_platform.sharing.sharing_service import ExternalShareService, ShareLinkService
from collaboration_platform.workspace.member_service import WorkspaceMemberService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_ws_and_asset(repos, name="Asset"):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROMPT, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )
    return ws, asset


@pytest.mark.asyncio
async def test_permission_resolution_precedence(repos):
    ws, asset = await _make_ws_and_asset(repos, "perm")
    member_svc = WorkspaceMemberService(repos)
    await member_svc.add_member(ws.id, "user-2", role=WorkspaceRole.VIEWER)

    perm_svc = PermissionService(repos)
    # membership only -> VIEWER
    assert await perm_svc.effective_role(asset.id, "user-2") == WorkspaceRole.VIEWER

    # workspace-level grant upgrades it
    await perm_svc.grant_workspace_permission(ws.id, PrincipalType.USER, "user-2", WorkspaceRole.EDITOR, granted_by="user-1")
    assert await perm_svc.effective_role(asset.id, "user-2") == WorkspaceRole.EDITOR

    # asset-level override wins over the workspace grant
    await perm_svc.grant_asset_permission(asset.id, PrincipalType.USER, "user-2", WorkspaceRole.ADMIN, granted_by="user-1")
    assert await perm_svc.effective_role(asset.id, "user-2") == WorkspaceRole.ADMIN

    await perm_svc.require_role(asset.id, "user-2", minimum=WorkspaceRole.ADMIN)
    with pytest.raises(PermissionDeniedError):
        await perm_svc.require_role(asset.id, "user-3", minimum=WorkspaceRole.VIEWER)  # no access at all


@pytest.mark.asyncio
async def test_share_link_lifecycle(repos):
    ws, asset = await _make_ws_and_asset(repos, "sharelink")
    svc = ShareLinkService(repos)
    link, raw_token = await svc.create_link(asset.id, created_by="user-1", permission=SharePermission.COMMENT)

    resolved = await svc.resolve_link(raw_token)
    assert resolved.id == link.id

    await svc.revoke_link(link.id)
    with pytest.raises(ShareLinkRevokedError):
        await svc.resolve_link(raw_token)


@pytest.mark.asyncio
async def test_share_link_expiry(repos):
    ws, asset = await _make_ws_and_asset(repos, "expiry")
    svc = ShareLinkService(repos)
    link, raw_token = await svc.create_link(asset.id, created_by="user-1")
    link.expires_at = utcnow()
    await repos.sharing_links.update(link)
    with pytest.raises(ShareLinkExpiredError):
        await svc.resolve_link(raw_token)


@pytest.mark.asyncio
async def test_external_share_invite_and_disabled_flag(repos):
    ws, asset = await _make_ws_and_asset(repos, "external")
    svc = ExternalShareService(repos)
    with pytest.raises(ExternalSharingDisabledError):
        await svc.invite(asset.id, "partner@example.com", invited_by="user-1", external_sharing_enabled=False)

    share = await svc.invite(asset.id, "partner@example.com", invited_by="user-1")
    accepted = await svc.accept(share.id)
    assert accepted.accepted_at is not None
    revoked = await svc.revoke(share.id)
    assert revoked.revoked_at is not None


@pytest.mark.asyncio
async def test_audit_log_records_and_filters(repos):
    ws, asset = await _make_ws_and_asset(repos, "audit")
    svc = AuditService(repos)
    await svc.record(actor_id="user-1", action="asset.create", resource_type="asset", resource_id=asset.id, workspace_id=ws.id)
    await svc.record(actor_id="user-1", action="asset.archive", resource_type="asset", resource_id=asset.id, workspace_id=ws.id)

    all_entries = await svc.list_for_workspace(ws.id)
    assert len(all_entries) == 2
    archived_only = await svc.list_for_workspace(ws.id, action="asset.archive")
    assert len(archived_only) == 1


@pytest.mark.asyncio
async def test_retention_sweep_purges_only_expired_deleted_assets(repos):
    ws, asset = await _make_ws_and_asset(repos, "retention")
    asset_svc = CollaborationAssetService(repos)
    await asset_svc.archive(asset.id)
    deleted = await asset_svc.delete(asset.id)

    retention_svc = RetentionService(repos)
    # policy says retain 30 days -> a just-deleted asset should NOT be purged yet
    await retention_svc.set_policy(ws.id, resource_type="asset", retain_days=30, created_by="user-1")
    purged = await retention_svc.sweep_expired_assets(ws.id)
    assert purged == []
    assert await repos.assets.get(asset.id, include_deleted=True) is not None

    # backdate deleted_at beyond the retention window and sweep again
    from datetime import timedelta
    deleted.deleted_at = utcnow() - timedelta(days=31)
    await repos.assets.update(deleted)
    purged_again = await retention_svc.sweep_expired_assets(ws.id)
    assert purged_again == [asset.id]
    assert await repos.assets.get(asset.id, include_deleted=True) is None
