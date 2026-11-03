"""Observability aggregate metrics across activity, usage, sessions,
reviews, notifications, engagement, and growth.

Uses a unique subject id (`_OBS_USER`) rather than the generic
"user-2" placeholder other test files use, deliberately: this test's
`ReviewService.approve` call commits mid-transaction (see that
service's docstring — the commit has to span the lock for correctness
under real concurrency), which means the workspace-membership write
earlier in *this same test* is durably persisted rather than rolled
back by the usual per-test `db_session` teardown. A generic id shared
with other test files would make this test's exact-count assertions
(`workspace_count == 1`, etc.) fragile against whatever those other
files happen to commit — the same category of fix already applied
elsewhere in this build for cross-test data collisions (unique slugs,
unique emails), just triggered here by a commit instead of a unique
constraint."""
from __future__ import annotations

import pytest

from collaboration_platform.analytics.observability_service import ObservabilityService
from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.comments.comment_service import CommentService
from collaboration_platform.domain.enums import AssetType, NotificationType
from collaboration_platform.notifications.notification_service import NotificationService
from collaboration_platform.realtime.edit_session_service import EditSessionService
from collaboration_platform.reviews.review_service import ReviewService
from collaboration_platform.productivity.task_service import TaskService
from collaboration_platform.workspace.member_service import WorkspaceMemberService
from collaboration_platform.workspace.workspace_service import WorkspaceService


_OBS_USER = "obs-engagement-user"


@pytest.mark.asyncio
async def test_observability_across_the_board(repos):
    ws = await WorkspaceService(repos).create_workspace(name="Obs WS", owner_id="user-1")
    await WorkspaceMemberService(repos).add_member(ws.id, _OBS_USER)
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.PROMPT, external_ref_id="obs-1", name="Obs Asset", owner_id="user-1"
    )
    await CommentService(repos).add_comment(asset.id, _OBS_USER, "great work")
    await EditSessionService(repos).start_session(asset.id, _OBS_USER)

    review = await ReviewService(repos).request_review(asset.id, "user-1", reviewer_ids=[_OBS_USER])
    await ReviewService(repos).approve(review.id, _OBS_USER)

    task = await TaskService(repos).create_task(ws.id, title="Ship it", created_by="user-1", assignee_id=_OBS_USER)
    await TaskService(repos).start(task.id)
    await TaskService(repos).complete(task.id)

    await NotificationService(repos).notify(_OBS_USER, NotificationType.MENTION, "You were mentioned")

    obs = ObservabilityService(repos)

    activity_summary = await obs.collaboration_activity_summary(ws.id)
    assert activity_summary["asset_count"] == 1
    assert activity_summary["comment_count"] == 1
    assert activity_summary["review_count"] == 1

    usage = await obs.workspace_usage(ws.id)
    assert usage["member_count"] == 2
    assert usage["asset_count"] == 1
    assert usage["assets_by_type"] == {"prompt": 1}

    session_stats = await obs.editing_session_stats(asset.id)
    assert session_stats["active_editor_count"] == 1

    review_metrics = await obs.review_metrics(ws.id)
    assert review_metrics["approved"] == 1
    assert review_metrics["approval_rate"] == 1.0

    delivery_stats = await obs.notification_delivery_stats(_OBS_USER)
    assert delivery_stats["notification_count"] == 1

    engagement = await obs.user_engagement(_OBS_USER)
    assert engagement["tasks_completed"] == 1
    assert engagement["workspace_count"] == 1

    growth = await obs.workspace_growth(ws.id)
    assert growth["total_members"] == 2
    assert sum(growth["joins_by_day"].values()) == 2
