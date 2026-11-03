"""Security & governance API: RBAC grants, audit log, retention
sweeps."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import (
    get_audit_service,
    get_current_actor_id,
    get_current_tenant_id,
    get_permission_service,
    get_retention_orchestration_service,
)
from observability_platform.governance.audit_service import AuditService
from observability_platform.governance.permission_service import PermissionService
from observability_platform.governance.retention_service import RetentionOrchestrationService
from observability_platform.obs_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/governance", tags=["governance"])


class GrantAccessRequest(BaseModel):
    principal_id: str
    role: str
    component_id: str | None = None


@router.post("/grants", status_code=201)
async def grant_access(body: GrantAccessRequest, tenant_id: str = Depends(get_current_tenant_id), service: PermissionService = Depends(get_permission_service)):
    return to_dict(await service.grant(tenant_id, **body.model_dump()))


@router.delete("/grants/{grant_id}", status_code=204)
async def revoke_access(grant_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PermissionService = Depends(get_permission_service)):
    await service.revoke(tenant_id, grant_id)


@router.get("/effective-role")
async def effective_role(
    principal_id: str, tenant_id: str = Depends(get_current_tenant_id), component_id: str | None = None,
    service: PermissionService = Depends(get_permission_service),
):
    role = await service.effective_role(tenant_id, principal_id, component_id=component_id)
    return {"role": role.value if role else None}


class RecordAuditEntryRequest(BaseModel):
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict | None = None


@router.post("/audit", status_code=201)
async def record_audit_entry(
    body: RecordAuditEntryRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: AuditService = Depends(get_audit_service),
):
    return to_dict(await service.record(tenant_id, actor_id=actor_id, **body.model_dump()))


@router.get("/audit")
async def list_audit_entries(tenant_id: str = Depends(get_current_tenant_id), limit: int = 200, service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.list_recent(tenant_id, limit=limit))


@router.post("/retention/sweep")
async def sweep_retention(tenant_id: str = Depends(get_current_tenant_id), service: RetentionOrchestrationService = Depends(get_retention_orchestration_service)):
    return await service.sweep_all(tenant_id)
