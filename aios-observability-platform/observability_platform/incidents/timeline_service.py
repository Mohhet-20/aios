"""Append-only incident timeline — every state change, assignment, and
manually-added note goes through `add_event`, so the timeline is a
complete audit trail of "what happened and when" independent of the
incident row's current field values."""
from __future__ import annotations

from observability_platform.models.incidents import IncidentTimelineEventModel
from observability_platform.repositories.registry import RepositoryRegistry


class IncidentTimelineService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_event(
        self, tenant_id: str, incident_id: str, *, event_type: str, message: str, actor: str | None = None
    ) -> IncidentTimelineEventModel:
        event = IncidentTimelineEventModel(
            tenant_id=tenant_id, incident_id=incident_id, event_type=event_type, message=message, actor=actor
        )
        return await self.repos.incident_timeline_events.add(event)

    async def list_timeline(self, tenant_id: str, incident_id: str) -> list[IncidentTimelineEventModel]:
        return await self.repos.incident_timeline_events.list_for_incident(tenant_id, incident_id)
