"""RBAC grants, audit log queries, and a manual retention-sweep
trigger. Policy enforcement (`EvaluationPolicyService`'s concurrency/
rate-limit checks) is called internally by whatever starts a run — it
has no standalone endpoint since there's nothing for a caller to POST
beyond what starting a run already does."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.dependencies.dependencies import get_audit_service, get_rbac_service, get_retention_service
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.governance.audit_service import AuditService
from eval_platform.governance.rbac_service import RBACService
from eval_platform.governance.retention_service import RetentionService

router = APIRouter(prefix="/governance", tags=["governance"])


class GrantRoleRequest(BaseModel):
    principal_id: str
    resource_type: str
    resource_id: str
    role: str
    granted_by: str
    principal_type: str = "user"


@router.post("/grants", status_code=201)
async def grant_role(body: GrantRoleRequest, service: RBACService = Depends(get_rbac_service)):
    return to_dict(await service.grant_role(
        body.principal_id, resource_type=body.resource_type, resource_id=body.resource_id, role=body.role,
        granted_by=body.granted_by, principal_type=body.principal_type,
    ))


@router.post("/grants/revoke")
async def revoke_role(principal_id: str, resource_type: str, resource_id: str, service: RBACService = Depends(get_rbac_service)):
    return to_dict(await service.revoke_role(principal_id, resource_type=resource_type, resource_id=resource_id))


@router.get("/grants")
async def list_grants(principal_id: str, service: RBACService = Depends(get_rbac_service)):
    return to_dict_list(await service.list_grants_for_principal(principal_id))


@router.get("/grants/effective-role")
async def get_effective_role(principal_id: str, resource_type: str, resource_id: str, service: RBACService = Depends(get_rbac_service)):
    role = await service.get_effective_role(principal_id, resource_type=resource_type, resource_id=resource_id)
    return {"role": role.value if role else None}


# -- audit log ---------------------------------------------------------------------

@router.get("/audit-log/resource")
async def list_audit_log_for_resource(resource_type: str, resource_id: str, service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.list_for_resource(resource_type, resource_id))


@router.get("/audit-log/actor")
async def list_audit_log_for_actor(actor_id: str, service: AuditService = Depends(get_audit_service)):
    return to_dict_list(await service.list_for_actor(actor_id))


# -- retention -----------------------------------------------------------------------

@router.post("/retention/sweep-observability-events")
async def sweep_observability_events(service: RetentionService = Depends(get_retention_service)):
    removed = await service.sweep_observability_events()
    return {"removed": removed}
