"""Activity feed recording and per-scope querying tests."""
from __future__ import annotations

import pytest

from collaboration_platform.activity.activity_service import ActivityService
from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.domain.enums import ActivityEventType, AssetType
from collaboration_platform.projects.project_service import ProjectService
from collaboration_platform.workspace.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_activity_feed_scoped_queries(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Feed Test", owner_id="user-1", organization_id="org-1")
    project = await ProjectService(repos).create_project(ws.id, name="Launch")
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, project_id=project.id, asset_type=AssetType.WORKFLOW, external_ref_id="wf-1",
        name="Onboarding Flow", owner_id="user-1",
    )

    activity = ActivityService(repos)
    await activity.record(
        actor_id="user-1", event_type=ActivityEventType.WORKSPACE_CREATED, summary="created workspace",
        workspace_id=ws.id, organization_id="org-1",
    )
    await activity.record(
        actor_id="user-1", event_type=ActivityEventType.ASSET_CREATED, summary="created asset",
        workspace_id=ws.id, project_id=project.id, asset_id=asset.id, organization_id="org-1",
    )
    await activity.record(
        actor_id="user-2", event_type=ActivityEventType.COMMENT_ADDED, summary="commented on asset",
        workspace_id=ws.id, asset_id=asset.id, organization_id="org-1",
    )

    workspace_feed = await activity.feed_for_workspace(ws.id)
    assert len(workspace_feed) == 3
    # most recent first
    assert workspace_feed[0].event_type == ActivityEventType.COMMENT_ADDED.value

    project_feed = await activity.feed_for_project(project.id)
    assert len(project_feed) == 1

    asset_feed = await activity.feed_for_asset(asset.id)
    assert len(asset_feed) == 2

    user1_feed = await activity.feed_for_user("user-1")
    assert len(user1_feed) == 2

    org_feed = await activity.feed_for_organization("org-1")
    assert len(org_feed) == 3
