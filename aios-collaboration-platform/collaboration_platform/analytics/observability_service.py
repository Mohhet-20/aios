"""ObservabilityService: collaboration activity, workspace usage,
editing-session stats, review/approval metrics, notification delivery
health, user engagement, and workspace growth — every metric computed
on demand from the real tables rather than a maintained counter, the
same anti-drift philosophy every other AIOS platform's observability
layer follows (see the Identity Platform's tenancy quota usage, or the
Tool Platform's resource-usage-only-when-measured rule)."""
from __future__ import annotations

from collections import Counter, defaultdict

from collaboration_platform.domain.enums import ReviewStatus
from collaboration_platform.repositories.registry import RepositoryRegistry


class ObservabilityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def collaboration_activity_summary(self, workspace_id: str) -> dict:
        assets = await self.repos.assets.list_for_workspace(workspace_id)
        asset_ids = {a.id for a in assets}
        comment_count = 0
        version_count = 0
        review_count = 0
        for asset_id in asset_ids:
            comment_count += len(await self.repos.comments.list_for_asset(asset_id))
            version_count += len(await self.repos.versions.list_for_asset(asset_id))
            review_count += len(await self.repos.review_requests.list_for_asset(asset_id))
        activity_events = await self.repos.activity_events.list_for_workspace(workspace_id, limit=100000)
        return {
            "workspace_id": workspace_id, "asset_count": len(assets), "comment_count": comment_count,
            "version_count": version_count, "review_count": review_count, "activity_event_count": len(activity_events),
        }

    async def workspace_usage(self, workspace_id: str) -> dict:
        members = await self.repos.workspace_members.list_for_workspace(workspace_id)
        projects = await self.repos.projects.list_for_workspace(workspace_id)
        assets = await self.repos.assets.list_for_workspace(workspace_id)
        by_type = Counter(a.asset_type for a in assets)
        return {
            "workspace_id": workspace_id, "member_count": len(members), "project_count": len(projects),
            "asset_count": len(assets), "assets_by_type": dict(by_type),
        }

    async def editing_session_stats(self, asset_id: str) -> dict:
        active = await self.repos.edit_sessions.list_active_for_asset(asset_id)
        presence = await self.repos.presence_sessions.list_active_for_asset(asset_id)
        return {"asset_id": asset_id, "active_editor_count": len(active), "active_presence_count": len(presence)}

    async def review_metrics(self, workspace_id: str) -> dict:
        assets = await self.repos.assets.list_for_workspace(workspace_id)
        counts: Counter = Counter()
        for asset in assets:
            for review in await self.repos.review_requests.list_for_asset(asset.id):
                counts[review.status] += 1
        total_decided = counts[ReviewStatus.APPROVED.value] + counts[ReviewStatus.REJECTED.value]
        approval_rate = (counts[ReviewStatus.APPROVED.value] / total_decided) if total_decided else None
        return {
            "workspace_id": workspace_id, "pending": counts[ReviewStatus.PENDING.value] + counts[ReviewStatus.IN_REVIEW.value],
            "approved": counts[ReviewStatus.APPROVED.value], "rejected": counts[ReviewStatus.REJECTED.value],
            "cancelled": counts[ReviewStatus.CANCELLED.value], "approval_rate": approval_rate,
        }

    async def notification_delivery_stats(self, recipient_id: str) -> dict:
        notifications = await self.repos.notifications.list_for_recipient(recipient_id, limit=100000)
        by_status: Counter = Counter()
        by_channel: Counter = Counter()
        for notification in notifications:
            for delivery in await self.repos.notification_deliveries.list_for_notification(notification.id):
                by_status[delivery.status] += 1
                by_channel[delivery.channel] += 1
        return {
            "recipient_id": recipient_id, "notification_count": len(notifications),
            "deliveries_by_status": dict(by_status), "deliveries_by_channel": dict(by_channel),
        }

    async def user_engagement(self, user_id: str) -> dict:
        tasks_completed = len([t for t in await self.repos.tasks.list_for_assignee(user_id, status="done")])
        recent_activity = await self.repos.activity_events.list_for_actor(user_id, limit=1000)
        workspaces = await self.repos.workspace_members.list_for_user(user_id)
        return {
            "user_id": user_id, "tasks_completed": tasks_completed, "activity_event_count": len(recent_activity),
            "workspace_count": len(workspaces),
        }

    async def workspace_growth(self, workspace_id: str) -> dict:
        """Buckets member-join dates by day — a simple growth curve
        derived from the membership table's own `created_at`, with no
        separate time-series table to keep in sync."""
        members = await self.repos.workspace_members.list_for_workspace(workspace_id)
        by_day: defaultdict[str, int] = defaultdict(int)
        for member in members:
            day = member.created_at.date().isoformat()
            by_day[day] += 1
        return {"workspace_id": workspace_id, "total_members": len(members), "joins_by_day": dict(sorted(by_day.items()))}
