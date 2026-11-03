"""Security & Governance: RBAC grants, retention policy configuration,
the audit trail, and compliance snapshots — the admin/compliance surface."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from memory_platform.domain.enums import RetentionAction, Role
from memory_platform.governance.audit_service import AuditService
from memory_platform.governance.compliance import resource_compliance_snapshot, workspace_compliance_snapshot
from memory_platform.governance.rbac_service import RBACService
from memory_platform.governance.retention_policy_service import RetentionPolicyService
from memory_platform.memory_api.dependencies import get_audit_service, get_current_actor_id, get_rbac_service, get_repos, get_retention_policy_service
from memory_platform.memory_api.serialization import to_dict, to_dict_list
from memory_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/workspaces/{workspace_id}/governance", tags=["governance"])


class GrantRequest(BaseModel):
    principal_id: str
    resource_type: str
    resource_id: str
    role: Role
    principal_type: str = "user"


class CreateRetentionPolicyRequest(BaseModel):
    retention_days: int
    action_on_expiry: RetentionAction
    memory_type: str | None = None
    scope_type: str | None = None


class AuditRecordRequest(BaseModel):
    action: str
    resource_type: str
    resource_id: str
    before: dict | None = None
    after: dict | None = None


@router.post("/rbac/grants", status_code=201)
async def grant_role(workspace_id: str, body: GrantRequest, actor_id: str = Depends(get_current_actor_id), svc: RBACService = Depends(get_rbac_service)):
    return to_dict(await svc.grant_role(principal_id=body.principal_id, resource_type=body.resource_type, resource_id=body.resource_id, role=body.role, granted_by=actor_id, principal_type=body.principal_type))


@router.delete("/rbac/grants/{grant_id}", status_code=204)
async def revoke_role(workspace_id: str, grant_id: str, svc: RBACService = Depends(get_rbac_service)):
    await svc.revoke_role(grant_id)


@router.get("/rbac/principals/{principal_id}/grants")
async def list_grants_for_principal(workspace_id: str, principal_id: str, svc: RBACService = Depends(get_rbac_service)):
    return to_dict_list(await svc.list_grants_for_principal(principal_id))


@router.get("/rbac/resolve-role")
async def resolve_role(workspace_id: str, principal_id: str, resource_type: str | None = None, resource_id: str | None = None, svc: RBACService = Depends(get_rbac_service)):
    role = await svc.resolve_role(principal_id=principal_id, workspace_id=workspace_id, resource_type=resource_type, resource_id=resource_id)
    return {"role": role.value if role else None}


@router.post("/retention-policies", status_code=201)
async def create_retention_policy(workspace_id: str, body: CreateRetentionPolicyRequest, svc: RetentionPolicyService = Depends(get_retention_policy_service)):
    return to_dict(await svc.create_policy(workspace_id=workspace_id, retention_days=body.retention_days, action_on_expiry=body.action_on_expiry, memory_type=body.memory_type, scope_type=body.scope_type))


@router.get("/retention-policies")
async def list_retention_policies(workspace_id: str, svc: RetentionPolicyService = Depends(get_retention_policy_service)):
    return to_dict_list(await svc.list_policies(workspace_id))


@router.post("/retention-policies/apply")
async def apply_retention_policies(workspace_id: str, actor_id: str = Depends(get_current_actor_id), svc: RetentionPolicyService = Depends(get_retention_policy_service)):
    return await svc.apply_workspace_retention_policies(workspace_id, actor_id=actor_id)


@router.post("/audit-log", status_code=201)
async def record_audit_entry(workspace_id: str, body: AuditRecordRequest, actor_id: str = Depends(get_current_actor_id), svc: AuditService = Depends(get_audit_service)):
    return to_dict(await svc.record(actor_id=actor_id, action=body.action, resource_type=body.resource_type, resource_id=body.resource_id, before=body.before, after=body.after))


@router.get("/audit-log/{resource_type}/{resource_id}")
async def get_audit_trail(workspace_id: str, resource_type: str, resource_id: str, svc: AuditService = Depends(get_audit_service)):
    return to_dict_list(await svc.get_audit_trail(resource_type, resource_id))


@router.get("/compliance/resource/{resource_type}/{resource_id}")
async def get_resource_compliance_snapshot(workspace_id: str, resource_type: str, resource_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return asdict(await resource_compliance_snapshot(repos, resource_type, resource_id))


@router.get("/compliance")
async def get_workspace_compliance_snapshot(workspace_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return asdict(await workspace_compliance_snapshot(repos, workspace_id))
