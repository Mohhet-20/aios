"""Postmortems: one per incident, only writable once the incident has
actually reached resolved/closed — writing a postmortem for a still-open
incident would encode conclusions about a fire that isn't out yet."""
from __future__ import annotations

from observability_platform.core.exceptions import IncidentError
from observability_platform.database.base import utcnow
from observability_platform.models.incidents import IncidentPostmortemModel
from observability_platform.repositories.registry import RepositoryRegistry


class PostmortemService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_or_update(
        self,
        tenant_id: str,
        incident_id: str,
        *,
        summary: str,
        root_cause_analysis: str | None = None,
        action_items: list | None = None,
        kb_links: list | None = None,
    ) -> IncidentPostmortemModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        if incident.status not in ("resolved", "closed"):
            raise IncidentError(
                f"Cannot write a postmortem for incident '{incident_id}' while it is still {incident.status}"
            )
        existing = await self.repos.incident_postmortems.get_for_incident(tenant_id, incident_id)
        if existing is not None:
            existing.summary = summary
            existing.root_cause_analysis = root_cause_analysis
            existing.action_items = action_items or []
            existing.kb_links = kb_links or []
            return await self.repos.incident_postmortems.update(existing)
        postmortem = IncidentPostmortemModel(
            tenant_id=tenant_id, incident_id=incident_id, summary=summary,
            root_cause_analysis=root_cause_analysis, action_items=action_items or [], kb_links=kb_links or [],
        )
        return await self.repos.incident_postmortems.add(postmortem)

    async def publish(self, tenant_id: str, incident_id: str) -> IncidentPostmortemModel:
        postmortem = await self.repos.incident_postmortems.get_for_incident(tenant_id, incident_id)
        if postmortem is None:
            raise IncidentError(f"No postmortem exists yet for incident '{incident_id}'")
        postmortem.published_at = utcnow()
        return await self.repos.incident_postmortems.update(postmortem)
