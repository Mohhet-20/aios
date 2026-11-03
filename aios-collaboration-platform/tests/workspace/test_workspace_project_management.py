"""Workspace/project/folder/collection/tag/favorite management tests."""
from __future__ import annotations

import pytest

from collaboration_platform.core.exceptions import ConflictError, InvalidTransitionError, PermissionDeniedError, ValidationError
from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.domain.enums import AssetType, WorkspaceRole, WorkspaceType
from collaboration_platform.projects.collection_service import CollectionService
from collaboration_platform.projects.favorite_service import FavoriteService
from collaboration_platform.projects.folder_service import FolderService
from collaboration_platform.projects.project_service import ProjectService
from collaboration_platform.projects.tag_service import TagService
from collaboration_platform.workspace.member_service import WorkspaceMemberService, role_at_least
from collaboration_platform.workspace.template_service import WorkspaceTemplateService
from collaboration_platform.workspace.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_create_workspace_seeds_owner_membership(repos):
    svc = WorkspaceService(repos)
    ws = await svc.create_workspace(name="Growth Team", owner_id="user-1", workspace_type=WorkspaceType.TEAM)
    members = await WorkspaceMemberService(repos).list_members(ws.id)
    assert len(members) == 1
    assert members[0].role == WorkspaceRole.OWNER.value


@pytest.mark.asyncio
async def test_duplicate_workspace_slug_rejected(repos):
    svc = WorkspaceService(repos)
    await svc.create_workspace(name="Dup Slug", owner_id="user-1", slug="dup-slug")
    with pytest.raises(ConflictError):
        await svc.create_workspace(name="Other Name", owner_id="user-2", slug="dup-slug")


@pytest.mark.asyncio
async def test_workspace_archive_restore_guarded(repos):
    svc = WorkspaceService(repos)
    ws = await svc.create_workspace(name="Archivable", owner_id="user-1")
    with pytest.raises(InvalidTransitionError):
        await svc.restore(ws.id)  # already active
    archived = await svc.archive(ws.id)
    assert archived.status == "archived"
    with pytest.raises(InvalidTransitionError):
        await svc.archive(ws.id)  # already archived
    restored = await svc.restore(ws.id)
    assert restored.status == "active"


@pytest.mark.asyncio
async def test_workspace_role_hierarchy_and_require_role(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Role Test", owner_id="owner-1")
    member_svc = WorkspaceMemberService(repos)
    await member_svc.add_member(ws.id, "viewer-1", role=WorkspaceRole.VIEWER)

    assert role_at_least(WorkspaceRole.ADMIN, WorkspaceRole.EDITOR) is True
    assert role_at_least(WorkspaceRole.VIEWER, WorkspaceRole.EDITOR) is False

    await member_svc.require_role(ws.id, "owner-1", minimum=WorkspaceRole.OWNER)
    with pytest.raises(PermissionDeniedError):
        await member_svc.require_role(ws.id, "viewer-1", minimum=WorkspaceRole.EDITOR)


@pytest.mark.asyncio
async def test_project_and_folder_hierarchy(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Proj Test", owner_id="user-1")
    project = await ProjectService(repos).create_project(ws.id, name="Launch")
    root_folder = await FolderService(repos).create_folder(ws.id, name="Root", project_id=project.id)
    child_folder = await FolderService(repos).create_folder(ws.id, name="Child", parent_folder_id=root_folder.id)

    with pytest.raises(ValidationError):
        await FolderService(repos).move(root_folder.id, new_parent_folder_id=child_folder.id)  # would cycle

    moved = await FolderService(repos).move(child_folder.id, new_parent_folder_id=None)
    assert moved.parent_folder_id is None


@pytest.mark.asyncio
async def test_collection_tag_favorite_flow(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Lib Test", owner_id="user-1")
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROMPT, external_ref_id="ext-1", name="Prompt A", owner_id="user-1"
    )

    collection = await CollectionService(repos).create_collection(ws.id, name="Q3 Launch", owner_id="user-1")
    await CollectionService(repos).add_item(collection.id, asset.id, added_by="user-1")
    with pytest.raises(ConflictError):
        await CollectionService(repos).add_item(collection.id, asset.id, added_by="user-1")
    assert len(await CollectionService(repos).list_items(collection.id)) == 1

    tag = await TagService(repos).create_tag(ws.id, name="launch", color="#ff0000")
    await TagService(repos).tag_asset(asset.id, tag.id)
    assert len(await TagService(repos).list_tags_for_asset(asset.id)) == 1

    await FavoriteService(repos).add_favorite("user-2", asset.id)
    with pytest.raises(ConflictError):
        await FavoriteService(repos).add_favorite("user-2", asset.id)
    assert len(await FavoriteService(repos).list_for_user("user-2")) == 1
    await FavoriteService(repos).remove_favorite("user-2", asset.id)
    assert len(await FavoriteService(repos).list_for_user("user-2")) == 0


@pytest.mark.asyncio
async def test_builtin_templates_seed_idempotently(repos):
    svc = WorkspaceTemplateService(repos)
    first = await svc.seed_builtin_templates()
    second = await svc.seed_builtin_templates()
    assert first >= 1
    assert second == 0


@pytest.mark.asyncio
async def test_asset_lifecycle_guarded(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Asset Lifecycle", owner_id="user-1")
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.AGENT, external_ref_id="agent-1", name="Agent A", owner_id="user-1"
    )
    archived = await CollaborationAssetService(repos).archive(asset.id)
    assert archived.status == "archived"
    deleted = await CollaborationAssetService(repos).delete(archived.id)
    assert deleted.status == "deleted"
    with pytest.raises(InvalidTransitionError):
        await CollaborationAssetService(repos).restore(deleted.id)
