"""Safety & Governance: RBAC grants, approval gates, and the audit log —
the Approval Center frontend surface plus the compliance/admin API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_approval_service, get_audit_service, get_rbac_service
from agent_platform.agent_api.serialization import to_dict, to_dict_list
from agent_platform.domain.enums import Role
from agent_platform.permissions.rbac_service import RBACService
from agent_platform.policies.approval_service import ApprovalService
from agent_platform.policies.audit_service import AuditService

router = APIRouter(tags=["governance"])


class GrantRequest(BaseModel):
    principal_id: str
    resource_type: str
    resource_id: str
    role: Role
    granted_by: str
    principal_type: str = "user"


class ApprovalRequestBody(BaseModel):
    reason: str
    requested_by_agent_id: str | None = None
    sensitivity_level: str = "normal"


class ApprovalDecisionRequest(BaseModel):
    approver_id: str
    notes: str | None = None


class AuditRecordRequest(BaseModel):
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    before: dict | None = None
    after: dict | None = None


@router.post("/rbac/grants", status_code=201)
async def grant(body: GrantRequest, svc: RBACService = Depends(get_rbac_service)):
    return to_dict(await svc.grant(body.principal_id, body.resource_type, body.resource_id, body.role, granted_by=body.granted_by, principal_type=body.principal_type))


@router.delete("/rbac/grants/{grant_id}", status_code=204)
async def revoke(grant_id: str, svc: RBACService = Depends(get_rbac_service)):
    await svc.revoke(grant_id)


@router.get("/rbac/principals/{principal_id}/grants")
async def list_grants(principal_id: str, svc: RBACService = Depends(get_rbac_service)):
    return to_dict_list(await svc.list_for_principal(principal_id))


@router.post("/tasks/{task_id}/approval-gates", status_code=201)
async def request_approval(task_id: str, body: ApprovalRequestBody, svc: ApprovalService = Depends(get_approval_service)):
    task = await svc.repos.tasks.get_or_404(task_id)
    return to_dict(await svc.request_approval(task, reason=body.reason, requested_by_agent_id=body.requested_by_agent_id, sensitivity_level=body.sensitivity_level))


@router.post("/approval-gates/{gate_id}/approve")
async def approve(gate_id: str, body: ApprovalDecisionRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.approve(gate_id, approver_id=body.approver_id, notes=body.notes))


@router.post("/approval-gates/{gate_id}/reject")
async def reject(gate_id: str, body: ApprovalDecisionRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.reject(gate_id, approver_id=body.approver_id, notes=body.notes))


@router.get("/approval-gates/pending")
async def list_pending_approvals(svc: ApprovalService = Depends(get_approval_service)):
    return to_dict_list(await svc.list_pending())


@router.get("/tasks/{task_id}/approval-gates")
async def list_approval_gates_for_task(task_id: str, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict_list(await svc.list_for_task(task_id))


@router.post("/audit-log", status_code=201)
async def record_audit_entry(body: AuditRecordRequest, svc: AuditService = Depends(get_audit_service)):
    return to_dict(await svc.record(body.actor_id, body.action, body.resource_type, body.resource_id, before=body.before, after=body.after))


@router.get("/audit-log/{resource_type}/{resource_id}")
async def list_audit_entries(resource_type: str, resource_id: str, svc: AuditService = Depends(get_audit_service)):
    return to_dict_list(await svc.list_for_resource(resource_type, resource_id))
