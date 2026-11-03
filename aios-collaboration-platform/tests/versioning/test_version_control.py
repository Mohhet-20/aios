"""Version snapshots, CAS guard, rollback, diff, branching, and merge
tests."""
from __future__ import annotations

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.core.exceptions import BranchError, ConflictError, InvalidReleaseTagError, MergeConflictError, StaleWriteError
from collaboration_platform.domain.enums import AssetType, BranchStatus, MergeStrategy
from collaboration_platform.versioning.branch_service import BranchService
from collaboration_platform.versioning.merge_service import MergeService
from collaboration_platform.versioning.version_service import VersionService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_asset(repos, name="Asset"):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    return await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROMPT, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )


@pytest.mark.asyncio
async def test_version_numbering_and_asset_head_tracking(repos):
    asset = await _make_asset(repos, "numbering")
    svc = VersionService(repos)
    v1 = await svc.create_version(asset.id, "user-1", {"text": "hello"})
    v2 = await svc.create_version(asset.id, "user-1", {"text": "hello world"})
    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v2.parent_version_id == v1.id

    refreshed = await repos.assets.get_or_404(asset.id)
    assert refreshed.current_version_id == v2.id


@pytest.mark.asyncio
async def test_cas_guard_rejects_stale_write(repos):
    asset = await _make_asset(repos, "cas")
    svc = VersionService(repos)
    v1 = await svc.create_version(asset.id, "user-1", {"text": "v1"})

    # caller declares they last saw v1 -> fine
    v2 = await svc.create_version(asset.id, "user-1", {"text": "v2"}, expected_base_version_id=v1.id)
    assert v2.version_number == 2

    # a second caller still thinks v1 is current -> rejected, since head is now v2
    with pytest.raises(StaleWriteError):
        await svc.create_version(asset.id, "user-2", {"text": "conflicting"}, expected_base_version_id=v1.id)


@pytest.mark.asyncio
async def test_rollback_creates_new_version_preserving_history(repos):
    asset = await _make_asset(repos, "rollback")
    svc = VersionService(repos)
    v1 = await svc.create_version(asset.id, "user-1", {"text": "v1"})
    await svc.create_version(asset.id, "user-1", {"text": "v2"})
    await svc.create_version(asset.id, "user-1", {"text": "v3"})

    rolled = await svc.rollback(asset.id, v1.id, created_by="user-2")
    assert rolled.version_number == 4  # new version, history not rewritten
    assert rolled.content_snapshot == {"text": "v1"}
    assert "Rolled back" in rolled.change_summary

    all_versions = await svc.list_versions(asset.id)
    assert len(all_versions) == 4


@pytest.mark.asyncio
async def test_compare_versions_diff(repos):
    asset = await _make_asset(repos, "diff")
    svc = VersionService(repos)
    v1 = await svc.create_version(asset.id, "user-1", {"a": 1, "b": 2})
    v2 = await svc.create_version(asset.id, "user-1", {"a": 1, "b": 3, "c": 4})

    diff = await svc.compare(v1.id, v2.id)
    assert diff["added"] == {"c": 4}
    assert diff["removed"] == {}
    assert diff["changed"] == {"b": {"from": 2, "to": 3}}
    assert "a" in diff["unchanged_keys"]


@pytest.mark.asyncio
async def test_release_tag_validation(repos):
    asset = await _make_asset(repos, "release")
    svc = VersionService(repos)
    with pytest.raises(InvalidReleaseTagError):
        await svc.create_version(asset.id, "user-1", {"x": 1}, is_release=True, release_tag="not-a-version")

    released = await svc.create_version(asset.id, "user-1", {"x": 1}, is_release=True, release_tag="v1.0.0")
    assert released.is_release is True
    assert len(await svc.list_releases(asset.id)) == 1


@pytest.mark.asyncio
async def test_branch_create_and_duplicate_rejected(repos):
    asset = await _make_asset(repos, "branch")
    version_svc = VersionService(repos)
    base = await version_svc.create_version(asset.id, "user-1", {"text": "base"})

    branch_svc = BranchService(repos)
    branch = await branch_svc.create_branch(asset.id, name="feature-x", created_by="user-1", base_version_id=base.id)
    assert branch.status == BranchStatus.OPEN.value

    with pytest.raises(ConflictError):
        await branch_svc.create_branch(asset.id, name="feature-x", created_by="user-1")


@pytest.mark.asyncio
async def test_merge_fast_forward_and_manual(repos):
    asset = await _make_asset(repos, "merge")
    version_svc = VersionService(repos)
    base = await version_svc.create_version(asset.id, "user-1", {"text": "base"})

    branch_svc = BranchService(repos)
    branch = await branch_svc.create_branch(asset.id, name="feature-y", created_by="user-1", base_version_id=base.id)
    feature_version = await version_svc.create_version(asset.id, "user-1", {"text": "feature work"}, branch_name="feature-y")
    await branch_svc.update_head(branch.id, feature_version.id)

    merge_svc = MergeService(repos)
    merge_record = await merge_svc.merge(branch.id, target_branch_name="main", merged_by="user-2", strategy=MergeStrategy.FAST_FORWARD)
    assert merge_record.strategy == MergeStrategy.FAST_FORWARD.value

    merged_version = await repos.versions.get_or_404(merge_record.merged_version_id)
    assert merged_version.content_snapshot == {"text": "feature work"}
    assert merged_version.branch_name == "main"

    reloaded_branch = await repos.branches.get_or_404(branch.id)
    assert reloaded_branch.status == BranchStatus.MERGED.value

    # already-merged branch cannot be merged again
    with pytest.raises(BranchError):
        await merge_svc.merge(branch.id, target_branch_name="main", merged_by="user-2")


@pytest.mark.asyncio
async def test_manual_merge_requires_reconciled_content(repos):
    asset = await _make_asset(repos, "manual-merge")
    version_svc = VersionService(repos)
    base = await version_svc.create_version(asset.id, "user-1", {"text": "base"})
    branch_svc = BranchService(repos)
    branch = await branch_svc.create_branch(asset.id, name="feature-z", created_by="user-1", base_version_id=base.id)
    feature_version = await version_svc.create_version(asset.id, "user-1", {"text": "wip"}, branch_name="feature-z")
    await branch_svc.update_head(branch.id, feature_version.id)

    merge_svc = MergeService(repos)
    with pytest.raises(MergeConflictError):
        await merge_svc.merge(branch.id, target_branch_name="main", merged_by="user-2", strategy=MergeStrategy.MANUAL)

    merged = await merge_svc.merge(
        branch.id, target_branch_name="main", merged_by="user-2", strategy=MergeStrategy.MANUAL,
        manual_content={"text": "reconciled by hand"},
    )
    merged_version = await repos.versions.get_or_404(merged.merged_version_id)
    assert merged_version.content_snapshot == {"text": "reconciled by hand"}
