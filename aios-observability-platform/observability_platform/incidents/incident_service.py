"""Incident lifecycle. Every transition both mutates the guarded
`Incident` domain entity (so illegal transitions raise the same
`InvalidTransitionError` every other lifecycle in this platform uses)
and appends a timeline event, so the timeline is never allowed to fall
behind the incident's real state."""
from __future__ import annotations

from observability_platform.core.exceptions import ValidationError
from observability_platform.domain.entities import Incident as IncidentEntity
from observability_platform.domain.enums import IncidentSeverity, IncidentStatus
from observability_platform.incidents.timeline_service import IncidentTimelineService
from observability_platform.models.incidents import IncidentModel
from observability_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: IncidentModel) -> IncidentEntity:
    return IncidentEntity(
        id=model.id, status=IncidentStatus(model.status), acknowledged_at=model.acknowledged_at,
        resolved_at=model.resolved_at, closed_at=model.closed_at,
    )


def _apply(model: IncidentModel, entity: IncidentEntity) -> IncidentModel:
    model.status = entity.status.value
    model.acknowledged_at = entity.acknowledged_at
    model.resolved_at = entity.resolved_at
    model.closed_at = entity.closed_at
    return model


class IncidentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.timeline = IncidentTimelineService(repos)

    async def create_incident(
        self,
        tenant_id: str,
        *,
        title: str,
        description: str | None = None,
        severity: str = IncidentSeverity.SEV3.value,
        component_id: str | None = None,
        alert_id: str | None = None,
        assigned_to: str | None = None,
        escalation_policy_id: str | None = None,
        created_by: str | None = None,
    ) -> IncidentModel:
        if severity not in {s.value for s in IncidentSeverity}:
            raise ValidationError(f"Unknown incident severity '{severity}'")
        incident = IncidentModel(
            tenant_id=tenant_id, title=title, description=description, severity=severity,
            component_id=component_id, alert_id=alert_id, assigned_to=assigned_to,
            escalation_policy_id=escalation_policy_id,
        )
        incident = await self.repos.incidents.add(incident)
        await self.timeline.add_event(tenant_id, incident.id, event_type="created", message=f"Incident opened: {title}", actor=created_by)
        return incident

    async def acknowledge(self, tenant_id: str, incident_id: str, *, by: str | None = None) -> IncidentModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        entity = _to_entity(incident)
        entity.acknowledge()
        incident = _apply(incident, entity)
        incident = await self.repos.incidents.update(incident)
        await self.timeline.add_event(tenant_id, incident_id, event_type="acknowledged", message="Investigation started", actor=by)
        return incident

    async def mark_identified(self, tenant_id: str, incident_id: str, *, root_cause: str | None = None, by: str | None = None) -> IncidentModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        entity = _to_entity(incident)
        entity.mark_identified()
        incident = _apply(incident, entity)
        if root_cause:
            incident.root_cause = root_cause
        incident = await self.repos.incidents.update(incident)
        await self.timeline.add_event(tenant_id, incident_id, event_type="identified", message=root_cause or "Root cause identified", actor=by)
        return incident

    async def mark_monitoring(self, tenant_id: str, incident_id: str, *, by: str | None = None) -> IncidentModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        entity = _to_entity(incident)
        entity.mark_monitoring()
        incident = _apply(incident, entity)
        incident = await self.repos.incidents.update(incident)
        await self.timeline.add_event(tenant_id, incident_id, event_type="monitoring", message="Fix deployed, monitoring for recurrence", actor=by)
        return incident

    async def resolve(self, tenant_id: str, incident_id: str, *, resolution_notes: str | None = None, by: str | None = None) -> IncidentModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        entity = _to_entity(incident)
        entity.resolve()
        incident = _apply(incident, entity)
        if resolution_notes:
            incident.resolution_notes = resolution_notes
        incident = await self.repos.incidents.update(incident)
        await self.timeline.add_event(tenant_id, incident_id, event_type="resolved", message=resolution_notes or "Incident resolved", actor=by)
        return incident

    async def reopen(self, tenant_id: str, incident_id: str, *, reason: str, by: str | None = None) -> IncidentModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        entity = _to_entity(incident)
        entity.reopen()
        incident = _apply(incident, entity)
        incident = await self.repos.incidents.update(incident)
        await self.timeline.add_event(tenant_id, incident_id, event_type="reopened", message=reason, actor=by)
        return incident

    async def close(self, tenant_id: str, incident_id: str, *, by: str | None = None) -> IncidentModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        entity = _to_entity(incident)
        entity.close()
        incident = _apply(incident, entity)
        incident = await self.repos.incidents.update(incident)
        await self.timeline.add_event(tenant_id, incident_id, event_type="closed", message="Incident closed", actor=by)
        return incident

    async def assign(self, tenant_id: str, incident_id: str, assignee: str, *, by: str | None = None) -> IncidentModel:
        incident = await self.repos.incidents.get_or_404(incident_id)
        incident.assigned_to = assignee
        incident = await self.repos.incidents.update(incident)
        await self.timeline.add_event(tenant_id, incident_id, event_type="assigned", message=f"Assigned to {assignee}", actor=by)
        return incident
