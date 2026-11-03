"""AI Governance API: governed-asset registry with lifecycle-stage
progression, and approval workflows."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from security_platform.dependencies.dependencies import (
    get_approval_workflow_service,
    get_current_actor_id,
    get_current_tenant_id,
    get_governance_asset_service,
)
from security_platform.governance.approval_service import ApprovalWorkflowService
from security_platform.governance.governance_service import GovernanceAssetService
from security_platform.sec_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/governance", tags=["governance"])


class RegisterAssetRequest(BaseModel):
    asset_type: str
    external_ref_id: str
    name: str
    owner_id: str | None = None


@router.post("/assets", status_code=201)
async def register_asset(
    body: RegisterAssetRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: GovernanceAssetService = Depends(get_governance_asset_service),
):
    return to_dict(await service.register_asset(tenant_id, **body.model_dump(), created_by=actor_id))


@router.post("/assets/{asset_id}/owner")
async def set_owner(asset_id: str, owner_id: str, tenant_id: str = Depends(get_current_tenant_id), service: GovernanceAssetService = Depends(get_governance_asset_service)):
    return to_dict(await service.set_owner(tenant_id, asset_id, owner_id))


@router.post("/assets/{asset_id}/advance-stage")
async def advance_stage(asset_id: str, target_stage: str, tenant_id: str = Depends(get_current_tenant_id), service: GovernanceAssetService = Depends(get_governance_asset_service)):
    return to_dict(await service.advance_stage(tenant_id, asset_id, target_stage))


@router.get("/assets")
async def list_by_stage(stage: str, tenant_id: str = Depends(get_current_tenant_id), service: GovernanceAssetService = Depends(get_governance_asset_service)):
    return to_dict_list(await service.list_by_stage(tenant_id, stage))


class RequestApprovalRequest(BaseModel):
    asset_id: str
    asset_type: str
    target_lifecycle_stage: str | None = None


@router.post("/approvals", status_code=201)
async def request_approval(
    body: RequestApprovalRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: ApprovalWorkflowService = Depends(get_approval_workflow_service),
):
    return to_dict(
        await service.request_approval(tenant_id, body.asset_id, asset_type=body.asset_type, requested_by=actor_id, target_lifecycle_stage=body.target_lifecycle_stage)
    )


class RecordDecisionRequest(BaseModel):
    decision: str
    comment: str | None = None


@router.post("/approvals/{request_id}/decisions", status_code=201)
async def record_decision(
    request_id: str, body: RecordDecisionRequest, tenant_id: str = Depends(get_current_tenant_id),
    actor_id: str | None = Depends(get_current_actor_id), service: ApprovalWorkflowService = Depends(get_approval_workflow_service),
):
    return to_dict(await service.record_decision(tenant_id, request_id, actor_id or "unknown", body.decision, comment=body.comment))


@router.post("/approvals/{request_id}/cancel")
async def cancel_request(request_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ApprovalWorkflowService = Depends(get_approval_workflow_service)):
    return to_dict(await service.cancel_request(tenant_id, request_id))


@router.get("/assets/{asset_id}/approvals/pending")
async def list_pending_for_asset(asset_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ApprovalWorkflowService = Depends(get_approval_workflow_service)):
    return to_dict_list(await service.list_pending_for_asset(tenant_id, asset_id))
