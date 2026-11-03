"""Smoke test: every repository in the registry is reachable and the
basic add/get/list round-trip works for a representative sample across
the whole schema (workspace -> project -> asset -> comment -> version
-> review -> notification -> activity)."""
from __future__ import annotations

import pytest

from collaboration_platform.models.activity import ActivityEventModel
from collaboration_platform.models.asset import CollaborationAssetModel
from collaboration_platform.models.comment import CommentModel
from collaboration_platform.models.notification import NotificationModel
from collaboration_platform.models.review import ReviewRequestModel
from collaboration_platform.models.version import VersionModel
from collaboration_platform.models.workspace import ProjectModel, WorkspaceModel


@pytest.mark.asyncio
async def test_full_registry_round_trip(repos):
    workspace = await repos.workspaces.add(WorkspaceModel(name="Acme Collab", slug="acme-collab-smoke", owner_id="user-1"))
    project = await repos.projects.add(ProjectModel(workspace_id=workspace.id, name="Launch", slug="launch"))
    asset = await repos.assets.add(
        CollaborationAssetModel(
            workspace_id=workspace.id, project_id=project.id, asset_type="prompt",
            external_ref_id="prompt-123", name="Welcome Prompt", owner_id="user-1",
        )
    )
    comment = await repos.comments.add(CommentModel(asset_id=asset.id, author_id="user-2", body="Looks good"))
    version = await repos.versions.add(
        VersionModel(asset_id=asset.id, version_number=1, content_snapshot={"text": "hello"}, created_by="user-1")
    )
    assert comment.body == "Looks good"
    assert version.version_number == 1
    review = await repos.review_requests.add(ReviewRequestModel(asset_id=asset.id, requested_by="user-1"))
    notification = await repos.notifications.add(
        NotificationModel(recipient_id="user-2", notification_type="mention", title="You were mentioned")
    )
    activity = await repos.activity_events.add(
        ActivityEventModel(workspace_id=workspace.id, actor_id="user-1", event_type="asset_created", summary="created asset")
    )
    assert review.status == "pending"
    assert notification.is_read is False
    assert activity.event_type == "asset_created"

    assert (await repos.workspaces.get_or_404(workspace.id)).slug == "acme-collab-smoke"
    assert len(await repos.projects.list_for_workspace(workspace.id)) == 1
    assert len(await repos.assets.list_for_workspace(workspace.id)) == 1
    assert len(await repos.comments.list_for_asset(asset.id)) == 1
    assert len(await repos.versions.list_for_asset(asset.id)) == 1
    assert len(await repos.review_requests.list_for_asset(asset.id)) == 1
    assert len(await repos.notifications.list_for_recipient("user-2")) == 1
    assert len(await repos.activity_events.list_for_workspace(workspace.id)) == 1

    # touch every remaining repository property to prove the registry wires cleanly
    for attr in (
        "workspace_templates", "workspace_members", "folders", "collections", "collection_items",
        "tags", "asset_tags", "favorites", "presence_sessions", "edit_sessions", "conflict_records",
        "comment_reactions", "comment_attachments", "mentions", "comment_edit_history",
        "notification_preferences", "notification_deliveries", "branches", "merges",
        "approval_policies", "review_assignments", "library_assets", "library_favorites",
        "saved_searches", "recent_items", "tasks", "checklists", "checklist_items", "bookmarks",
        "pinned_items", "workspace_permissions", "asset_permissions", "sharing_links",
        "external_shares", "audit_log_entries", "retention_policies",
    ):
        assert getattr(repos, attr) is not None
