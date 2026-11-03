"""Prompt Governance: permission grants, sensitive-prompt protection,
audit trail, compliance rollup."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.domain.enums import Role
from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_governance_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_governance.governance_service import GovernanceService

router = APIRouter(tags=["governance"])


class GrantPermissionRequest(BaseModel):
    resource_type: str
    resource_id: str
    principal_id: str
    role: Role
    principal_type: str = "user"


class SensitiveRequest(BaseModel):
    sensitive: bool


@router.post("/permissions", status_code=201)
async def grant_permission(body: GrantPermissionRequest, actor_id: str = Depends(get_current_actor_id), svc: GovernanceService = Depends(get_governance_service)):
    grant = await svc.grant_permission(body.resource_type, body.resource_id, body.principal_id, body.role, granted_by=actor_id, principal_type=body.principal_type)
    return to_dict(grant)


@router.delete("/permissions/{grant_id}", status_code=204)
async def revoke_permission(grant_id: str, actor_id: str = Depends(get_current_actor_id), svc: GovernanceService = Depends(get_governance_service)):
    await svc.revoke_permission(grant_id, actor_id=actor_id)


@router.get("/permissions/principal/{principal_id}")
async def list_grants_for_principal(principal_id: str, svc: GovernanceService = Depends(get_governance_service)):
    return to_dict_list(await svc.list_grants_for_principal(principal_id))


@router.get("/permissions/resource/{resource_type}/{resource_id}")
async def list_grants_for_resource(resource_type: str, resource_id: str, svc: GovernanceService = Depends(get_governance_service)):
    return to_dict_list(await svc.list_grants_for_resource(resource_type, resource_id))


@router.put("/prompts/{prompt_id}/sensitive")
async def set_sensitive(prompt_id: str, body: SensitiveRequest, actor_id: str = Depends(get_current_actor_id), svc: GovernanceService = Depends(get_governance_service)):
    return to_dict(await svc.set_sensitive(prompt_id, body.sensitive, actor_id=actor_id))


@router.get("/audit/{resource_type}/{resource_id}")
async def audit_trail(resource_type: str, resource_id: str, limit: int = 100, svc: GovernanceService = Depends(get_governance_service)):
    return to_dict_list(await svc.audit_trail(resource_type, resource_id, limit=limit))


@router.get("/prompts/{prompt_id}/compliance-report")
async def compliance_report(prompt_id: str, svc: GovernanceService = Depends(get_governance_service)):
    return await svc.compliance_report(prompt_id)
