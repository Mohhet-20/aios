"""Incident management API: lifecycle, assignment, timeline, and
postmortems."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import (
    get_current_actor_id,
    get_current_tenant_id,
    get_incident_service,
    get_incident_timeline_service,
    get_postmortem_service,
    get_repos,
)
from observability_platform.incidents.incident_service import IncidentService
from observability_platform.incidents.postmortem_service import PostmortemService
from observability_platform.incidents.timeline_service import IncidentTimelineService
from observability_platform.obs_api.serialization import to_dict, to_dict_list
from observability_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/incidents", tags=["incidents"])


class CreateIncidentRequest(BaseModel):
    title: str
    description: str | None = None
    severity: str = "sev3"
    component_id: str | None = None
    alert_id: str | None = None
    assigned_to: str | None = None
    escalation_policy_id: str | None = None


@router.post("", status_code=201)
async def create_incident(
    body: CreateIncidentRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: IncidentService = Depends(get_incident_service),
):
    return to_dict(await service.create_incident(tenant_id, created_by=actor_id, **body.model_dump()))


@router.get("")
async def list_incidents(tenant_id: str = Depends(get_current_tenant_id), status: str | None = None, repos: RepositoryRegistry = Depends(get_repos)):
    if status:
        return to_dict_list(await repos.incidents.list_by_status(tenant_id, status))
    return to_dict_list(await repos.incidents.list_open(tenant_id))


@router.post("/{incident_id}/acknowledge")
async def acknowledge(incident_id: str, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id), service: IncidentService = Depends(get_incident_service)):
    return to_dict(await service.acknowledge(tenant_id, incident_id, by=actor_id))


class MarkIdentifiedRequest(BaseModel):
    root_cause: str | None = None


@router.post("/{incident_id}/identify")
async def mark_identified(
    incident_id: str, body: MarkIdentifiedRequest, tenant_id: str = Depends(get_current_tenant_id),
    actor_id: str | None = Depends(get_current_actor_id), service: IncidentService = Depends(get_incident_service),
):
    return to_dict(await service.mark_identified(tenant_id, incident_id, root_cause=body.root_cause, by=actor_id))


@router.post("/{incident_id}/monitor")
async def mark_monitoring(incident_id: str, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id), service: IncidentService = Depends(get_incident_service)):
    return to_dict(await service.mark_monitoring(tenant_id, incident_id, by=actor_id))


class ResolveIncidentRequest(BaseModel):
    resolution_notes: str | None = None


@router.post("/{incident_id}/resolve")
async def resolve(
    incident_id: str, body: ResolveIncidentRequest, tenant_id: str = Depends(get_current_tenant_id),
    actor_id: str | None = Depends(get_current_actor_id), service: IncidentService = Depends(get_incident_service),
):
    return to_dict(await service.resolve(tenant_id, incident_id, resolution_notes=body.resolution_notes, by=actor_id))


class ReopenIncidentRequest(BaseModel):
    reason: str


@router.post("/{incident_id}/reopen")
async def reopen(
    incident_id: str, body: ReopenIncidentRequest, tenant_id: str = Depends(get_current_tenant_id),
    actor_id: str | None = Depends(get_current_actor_id), service: IncidentService = Depends(get_incident_service),
):
    return to_dict(await service.reopen(tenant_id, incident_id, reason=body.reason, by=actor_id))


@router.post("/{incident_id}/close")
async def close(incident_id: str, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id), service: IncidentService = Depends(get_incident_service)):
    return to_dict(await service.close(tenant_id, incident_id, by=actor_id))


class AssignIncidentRequest(BaseModel):
    assignee: str


@router.post("/{incident_id}/assign")
async def assign(
    incident_id: str, body: AssignIncidentRequest, tenant_id: str = Depends(get_current_tenant_id),
    actor_id: str | None = Depends(get_current_actor_id), service: IncidentService = Depends(get_incident_service),
):
    return to_dict(await service.assign(tenant_id, incident_id, body.assignee, by=actor_id))


@router.get("/{incident_id}/timeline")
async def timeline(incident_id: str, tenant_id: str = Depends(get_current_tenant_id), service: IncidentTimelineService = Depends(get_incident_timeline_service)):
    return to_dict_list(await service.list_timeline(tenant_id, incident_id))


class UpsertPostmortemRequest(BaseModel):
    summary: str
    root_cause_analysis: str | None = None
    action_items: list | None = None
    kb_links: list | None = None


@router.post("/{incident_id}/postmortem", status_code=201)
async def upsert_postmortem(
    incident_id: str, body: UpsertPostmortemRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PostmortemService = Depends(get_postmortem_service),
):
    return to_dict(await service.create_or_update(tenant_id, incident_id, **body.model_dump()))


@router.get("/{incident_id}/postmortem")
async def get_postmortem(incident_id: str, tenant_id: str = Depends(get_current_tenant_id), repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.incident_postmortems.get_for_incident(tenant_id, incident_id))


@router.post("/{incident_id}/postmortem/publish")
async def publish_postmortem(incident_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PostmortemService = Depends(get_postmortem_service)):
    return to_dict(await service.publish(tenant_id, incident_id))
