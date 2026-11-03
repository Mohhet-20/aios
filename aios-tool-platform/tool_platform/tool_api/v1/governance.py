"""Governance: RBAC grants, approval gates (request/approve/reject), and
the audit trail — the "Permission Manager" frontend surface."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.dependencies.dependencies import get_approval_service, get_audit_service, get_rbac_service
from tool_platform.governance.approval_service import ApprovalService
from tool_platform.governance.audit_service import AuditService
from tool_platform.governance.rbac_service import RBACService
from tool_platform.tool_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/governance", tags=["governance"])


class GrantRequest(BaseModel):
    principal_id: str
    resource_type: str
    resource_id: str
    role: str
    granted_by: str
    principal_type: str = "user"


class RequestApprovalRequest(BaseModel):
    resource_type: str
    resource_id: str
    requested_by: str
    reason: str | None = None
    sensitivity_level: str = "high"


class ApprovalDecisionRequest(BaseModel):
    approver_id: str
    notes: str | None = None


@router.post("/grants", status_code=201)
async def grant(body: GrantRequest, svc: RBACService = Depends(get_rbac_service)):
    return to_dict(await svc.grant(
        body.principal_id, body.resource_type, body.resource_id, body.role,
        granted_by=body.granted_by, principal_type=body.principal_type,
    ))


@router.post("/grants/{grant_id}/revoke")
async def revoke(grant_id: str, svc: RBACService = Depends(get_rbac_service)):
    return to_dict(await svc.revoke(grant_id))


@router.get("/grants")
async def list_for_principal(principal_id: str, svc: RBACService = Depends(get_rbac_service)):
    return to_dict_list(await svc.list_for_principal(principal_id))


@router.post("/approvals", status_code=201)
async def request_approval(body: RequestApprovalRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.request_approval(
        body.resource_type, body.resource_id, requested_by=body.requested_by, reason=body.reason,
        sensitivity_level=body.sensitivity_level,
    ))


@router.post("/approvals/{gate_id}/approve")
async def approve(gate_id: str, body: ApprovalDecisionRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.approve(gate_id, approver_id=body.approver_id, notes=body.notes))


@router.post("/approvals/{gate_id}/reject")
async def reject(gate_id: str, body: ApprovalDecisionRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.reject(gate_id, approver_id=body.approver_id, notes=body.notes))


@router.get("/approvals/pending")
async def list_pending(resource_type: str | None = None, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict_list(await svc.list_pending(resource_type=resource_type))


@router.get("/approvals")
async def list_for_resource(resource_type: str, resource_id: str, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict_list(await svc.list_for_resource(resource_type, resource_id))


@router.get("/audit-log")
async def list_audit_log(
    resource_type: str | None = None, resource_id: str | None = None, actor_id: str | None = None,
    limit: int = 100, svc: AuditService = Depends(get_audit_service),
):
    if resource_type and resource_id:
        return to_dict_list(await svc.list_for_resource(resource_type, resource_id, limit=limit))
    if actor_id:
        return to_dict_list(await svc.list_for_actor(actor_id, limit=limit))
    return []
