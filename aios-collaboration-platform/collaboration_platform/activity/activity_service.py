"""ActivityService: the single append-only event log every activity
feed (personal/project/workspace/organization) reads from — one
`record()` call site shape, filtered differently per feed by the
repository layer, rather than separate per-scope tables that could
drift out of sync with each other (see `ActivityEventModel`'s
docstring). Other services (workspace, comments, versions, reviews,
tasks) call `record()` as a side effect of their own writes; this
service itself only owns reading/writing the log, not deciding what's
worth logging."""
from __future__ import annotations

from collaboration_platform.domain.enums import ActivityEventType
from collaboration_platform.models.activity import ActivityEventModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class ActivityService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(
        self, *, actor_id: str, event_type: ActivityEventType, summary: str, workspace_id: str | None = None,
        project_id: str | None = None, asset_id: str | None = None, organization_id: str | None = None,
        event_metadata: dict | None = None,
    ) -> ActivityEventModel:
        return await self.repos.activity_events.add(ActivityEventModel(
            workspace_id=workspace_id, project_id=project_id, asset_id=asset_id, organization_id=organization_id,
            actor_id=actor_id, event_type=event_type.value, summary=summary, event_metadata=event_metadata or {},
        ))

    async def feed_for_workspace(self, workspace_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        return await self.repos.activity_events.list_for_workspace(workspace_id, limit=limit)

    async def feed_for_project(self, project_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        return await self.repos.activity_events.list_for_project(project_id, limit=limit)

    async def feed_for_asset(self, asset_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        return await self.repos.activity_events.list_for_asset(asset_id, limit=limit)

    async def feed_for_user(self, actor_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        return await self.repos.activity_events.list_for_actor(actor_id, limit=limit)

    async def feed_for_organization(self, organization_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        return await self.repos.activity_events.list_for_organization(organization_id, limit=limit)
