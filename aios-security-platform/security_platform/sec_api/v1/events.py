"""Security Events & Audit API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import get_audit_service, get_current_actor_id, get_current_tenant_id, get_security_event_service
from security_platform.audit.audit_service import AuditService
from security_platform.events.security_event_service import SecurityEventService
from security_platform.sec_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/security-events", tags=["security-events"])


class RecordEventRequest(BaseModel):
    event_type: str
    description: str
    severity: str = "info"
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None


@router.post("", status_code=201)
async def record_event(
    body: RecordEventRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: SecurityEventService = Depends(get_security_event_service),
):
    return to_dict(await service.record_event(tenant_id, body.event_type, description=body.description, severity=body.severity, actor_id=actor_id, resource_type=body.resource_type, resource_id=body.resource_id, details=body.details))


@router.get("")
async def list_recent(
    event_type: str | None = None, severity: str | None = None, limit: int = 200, tenant_id: str = Depends(get_current_tenant_id),
    service: SecurityEventService = Depends(get_security_event_service),
):
    return to_dict_list(await service.list_recent(tenant_id, event_type=event_type, severity=severity, limit=limit))


@router.get("/counts")
async def counts_by_type(since_hours: int | None = None, tenant_id: str = Depends(get_current_tenant_id), service: SecurityEventService = Depends(get_security_event_service)):
    return await service.counts_by_type(tenant_id, since_hours=since_hours)


audit_router = APIRouter(prefix="/audit-log", tags=["audit"])


class RecordAuditEntryRequest(BaseModel):
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict | None = None


@audit_router.post("", status_code=201)
async def record_audit_entry(
    body: RecordAuditEntryRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: AuditService = Depends(get_audit_service),
):
    return to_dict(await service.record(tenant_id, action=body.action, resource_type=body.resource_type, resource_id=body.resource_id, actor_id=actor_id, details=body.details))


@audit_router.get("/resource/{resource_type}/{resource_id}")
async def history_for_resource(resource_type: str, resource_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.history_for_resource(tenant_id, resource_type, resource_id))


@audit_router.get("/actor/{actor_id}")
async def history_for_actor(actor_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.history_for_actor(tenant_id, actor_id))


@audit_router.get("")
async def recent(limit: int = 200, tenant_id: str = Depends(get_current_tenant_id), service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.recent(tenant_id, limit=limit))
