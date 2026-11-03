"""Human-in-the-Loop surface: approve/reject multi-step approval chains,
reassign, escalate, expire, and comment — the manual-review side of the
engine. Approving/rejecting only updates the ApprovalRequest; resuming the
paused execution is a separate call to POST /executions/{id}/resume-after-approval."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.approval.approval_service import ApprovalService
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_api.dependencies import get_approval_service, get_repos
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecisionRequest(BaseModel):
    decided_by: str
    notes: str | None = None


class ReassignRequest(BaseModel):
    new_approvers: list[str]
    reassigned_by: str


class CommentRequest(BaseModel):
    author_id: str
    comment: str


@router.get("/{approval_id}")
async def get_approval(approval_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.approvals.get_or_404(approval_id))


@router.get("")
async def list_approvals(workspace_id: str | None = None, execution_id: str | None = None, svc: ApprovalService = Depends(get_approval_service)):
    if execution_id:
        return to_dict_list(await svc.list_for_execution(execution_id))
    if workspace_id:
        return to_dict_list(await svc.list_pending_for_workspace(workspace_id))
    return []


@router.post("/{approval_id}/approve")
async def approve_step(approval_id: str, body: DecisionRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.approve_step(approval_id, decided_by=body.decided_by, notes=body.notes))


@router.post("/{approval_id}/reject")
async def reject(approval_id: str, body: DecisionRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.reject(approval_id, decided_by=body.decided_by, notes=body.notes))


@router.post("/{approval_id}/reassign")
async def reassign_step(approval_id: str, body: ReassignRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.reassign_step(approval_id, new_approvers=body.new_approvers, reassigned_by=body.reassigned_by))


@router.post("/{approval_id}/escalate")
async def escalate(approval_id: str, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.escalate(approval_id))


@router.post("/escalation-sweep")
async def run_escalation_sweep(svc: ApprovalService = Depends(get_approval_service)):
    return to_dict_list(await svc.run_escalation_sweep())


@router.post("/{approval_id}/expire")
async def expire(approval_id: str, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.expire(approval_id))


@router.post("/{approval_id}/comments", status_code=201)
async def add_comment(approval_id: str, body: CommentRequest, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict(await svc.add_comment(approval_id, author_id=body.author_id, comment=body.comment))


@router.get("/{approval_id}/comments")
async def list_comments(approval_id: str, svc: ApprovalService = Depends(get_approval_service)):
    return to_dict_list(await svc.list_comments(approval_id))
