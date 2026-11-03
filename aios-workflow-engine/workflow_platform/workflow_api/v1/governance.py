"""Security & Governance surface: RBAC grants/effective-permission checks
and audit log queries. Workspace/organization isolation and execution/
approval policy enforcement (isolation.py, policy_service.py) are applied
internally by the engine/services rather than exposed as endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.domain.enums import Role
from workflow_platform.security.audit_service import AuditService
from workflow_platform.security.rbac_service import RBACService
from workflow_platform.workflow_api.dependencies import get_audit_service, get_current_actor_id, get_rbac_service
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list

router = APIRouter(tags=["governance"])


class GrantRequest(BaseModel):
    principal_id: str
    resource_type: str
    resource_id: str
    role: str
    principal_type: str = "user"


@router.post("/rbac/grants", status_code=201)
async def grant(body: GrantRequest, actor_id: str = Depends(get_current_actor_id), svc: RBACService = Depends(get_rbac_service)):
    return to_dict(await svc.grant(
        body.principal_id, body.resource_type, body.resource_id, Role(body.role), granted_by=actor_id,
        principal_type=body.principal_type,
    ))


@router.delete("/rbac/grants/{grant_id}", status_code=204)
async def revoke(grant_id: str, actor_id: str = Depends(get_current_actor_id), svc: RBACService = Depends(get_rbac_service)):
    await svc.revoke(grant_id, revoked_by=actor_id)


@router.get("/rbac/grants/by-principal/{principal_id}")
async def list_grants_for_principal(principal_id: str, svc: RBACService = Depends(get_rbac_service)):
    return to_dict_list(await svc.list_grants_for_principal(principal_id))


@router.get("/rbac/grants/by-resource/{resource_type}/{resource_id}")
async def list_grants_for_resource(resource_type: str, resource_id: str, svc: RBACService = Depends(get_rbac_service)):
    return to_dict_list(await svc.list_grants_for_resource(resource_type, resource_id))


@router.get("/rbac/effective-permissions")
async def get_effective_permissions(principal_id: str, workspace_id: str, workflow_id: str | None = None, svc: RBACService = Depends(get_rbac_service)):
    perms = await svc.get_effective_permissions(principal_id, workspace_id=workspace_id, workflow_id=workflow_id)
    return {"permissions": sorted(p.value for p in perms)}


@router.get("/audit-log/by-resource/{resource_type}/{resource_id}")
async def list_audit_for_resource(resource_type: str, resource_id: str, limit: int = 100, svc: AuditService = Depends(get_audit_service)):
    return to_dict_list(await svc.list_for_resource(resource_type, resource_id, limit=limit))


@router.get("/audit-log/by-actor/{actor_id}")
async def list_audit_for_actor(actor_id: str, limit: int = 100, svc: AuditService = Depends(get_audit_service)):
    return to_dict_list(await svc.list_for_actor(actor_id, limit=limit))
