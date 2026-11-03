"""Tests for AI Governance: asset registry (idempotent registration,
forward-only lifecycle progression with a deprecate/retire kill
switch), and approval workflows (policy-driven required-approval
counts, multi-approver threshold crossing, rejection, cancellation,
and lifecycle promotion on approval)."""
from __future__ import annotations

import pytest

from security_platform.core.exceptions import ApprovalAlreadyDecidedError, InvalidTransitionError, ValidationError
from security_platform.domain.enums import ApprovalStatus, LifecycleStage
from security_platform.governance.approval_service import ApprovalWorkflowService
from security_platform.governance.governance_service import GovernanceAssetService
from security_platform.models.governance import ApprovalPolicyModel

TENANT = "tenant-gov"


@pytest.mark.asyncio
async def test_register_asset_is_idempotent_on_external_ref(repos):
    service = GovernanceAssetService(repos)
    first = await service.register_asset(TENANT, asset_type="model", external_ref_id="model-123", name="Fraud Classifier")
    second = await service.register_asset(TENANT, asset_type="model", external_ref_id="model-123", name="Fraud Classifier v2 name ignored")
    assert first.id == second.id
    assert first.lifecycle_stage == LifecycleStage.DRAFT.value


@pytest.mark.asyncio
async def test_register_asset_rejects_unknown_type(repos):
    service = GovernanceAssetService(repos)
    with pytest.raises(ValidationError):
        await service.register_asset(TENANT, asset_type="spaceship", external_ref_id="x", name="x")


@pytest.mark.asyncio
async def test_advance_stage_forward_step_by_step(repos):
    service = GovernanceAssetService(repos)
    asset = await service.register_asset(TENANT, asset_type="prompt", external_ref_id="prompt-1", name="Support Reply Prompt")
    asset = await service.advance_stage(TENANT, asset.id, LifecycleStage.REVIEW.value)
    assert asset.lifecycle_stage == LifecycleStage.REVIEW.value
    asset = await service.advance_stage(TENANT, asset.id, LifecycleStage.APPROVED.value)
    assert asset.lifecycle_stage == LifecycleStage.APPROVED.value


@pytest.mark.asyncio
async def test_advance_stage_rejects_skipping_ahead(repos):
    service = GovernanceAssetService(repos)
    asset = await service.register_asset(TENANT, asset_type="prompt", external_ref_id="prompt-2", name="Another Prompt")
    with pytest.raises(ValidationError):
        await service.advance_stage(TENANT, asset.id, LifecycleStage.PRODUCTION.value)


@pytest.mark.asyncio
async def test_advance_stage_kill_switch_deprecate_from_draft(repos):
    service = GovernanceAssetService(repos)
    asset = await service.register_asset(TENANT, asset_type="dataset", external_ref_id="ds-1", name="Training Set")
    asset = await service.advance_stage(TENANT, asset.id, LifecycleStage.DEPRECATED.value)
    assert asset.lifecycle_stage == LifecycleStage.DEPRECATED.value


@pytest.mark.asyncio
async def test_set_owner_updates_asset(repos):
    service = GovernanceAssetService(repos)
    asset = await service.register_asset(TENANT, asset_type="agent", external_ref_id="agent-1", name="Support Agent")
    updated = await service.set_owner(TENANT, asset.id, "user-owner-1")
    assert updated.owner_id == "user-owner-1"


@pytest.mark.asyncio
async def test_approval_uses_default_required_approvals_when_no_policy(repos):
    gov = GovernanceAssetService(repos)
    approvals = ApprovalWorkflowService(repos)
    asset = await gov.register_asset(TENANT, asset_type="model", external_ref_id="model-2", name="Model Two")
    request = await approvals.request_approval(TENANT, asset.id, asset_type="model")
    assert request.required_approvals == approvals.settings.default_required_approvals
    assert request.status == ApprovalStatus.PENDING.value


@pytest.mark.asyncio
async def test_approval_policy_overrides_required_count(repos):
    await repos.approval_policies.add(
        ApprovalPolicyModel(tenant_id=TENANT, asset_type="workflow", required_approvals=2, approver_roles=["security_admin"])
    )
    gov = GovernanceAssetService(repos)
    approvals = ApprovalWorkflowService(repos)
    asset = await gov.register_asset(TENANT, asset_type="workflow", external_ref_id="wf-1", name="Refund Workflow")
    request = await approvals.request_approval(TENANT, asset.id, asset_type="workflow")
    assert request.required_approvals == 2


@pytest.mark.asyncio
async def test_multi_approver_threshold_promotes_asset_on_final_approval(repos):
    await repos.approval_policies.add(
        ApprovalPolicyModel(tenant_id=TENANT, asset_type="workflow", required_approvals=2, approver_roles=["security_admin"])
    )
    gov = GovernanceAssetService(repos)
    approvals = ApprovalWorkflowService(repos)
    asset = await gov.register_asset(TENANT, asset_type="workflow", external_ref_id="wf-2", name="Payout Workflow")
    request = await approvals.request_approval(TENANT, asset.id, asset_type="workflow", target_lifecycle_stage=LifecycleStage.APPROVED.value)

    after_first = await approvals.record_decision(TENANT, request.id, "approver-1", "approve")
    assert after_first.status == ApprovalStatus.IN_REVIEW.value
    refreshed_asset = await repos.governance_assets.get(asset.id)
    assert refreshed_asset.lifecycle_stage == LifecycleStage.DRAFT.value  # not promoted yet

    after_second = await approvals.record_decision(TENANT, request.id, "approver-2", "approve")
    assert after_second.status == ApprovalStatus.APPROVED.value
    assert after_second.decided_at is not None
    promoted_asset = await repos.governance_assets.get(asset.id)
    assert promoted_asset.lifecycle_stage == LifecycleStage.APPROVED.value


@pytest.mark.asyncio
async def test_reject_decision_finalizes_request(repos):
    gov = GovernanceAssetService(repos)
    approvals = ApprovalWorkflowService(repos)
    asset = await gov.register_asset(TENANT, asset_type="model", external_ref_id="model-3", name="Risky Model")
    request = await approvals.request_approval(TENANT, asset.id, asset_type="model")
    rejected = await approvals.record_decision(TENANT, request.id, "approver-1", "reject", comment="Insufficient eval coverage.")
    assert rejected.status == ApprovalStatus.REJECTED.value

    with pytest.raises(ApprovalAlreadyDecidedError):
        await approvals.record_decision(TENANT, request.id, "approver-2", "approve")


@pytest.mark.asyncio
async def test_cancel_request(repos):
    gov = GovernanceAssetService(repos)
    approvals = ApprovalWorkflowService(repos)
    asset = await gov.register_asset(TENANT, asset_type="model", external_ref_id="model-4", name="Withdrawn Model")
    request = await approvals.request_approval(TENANT, asset.id, asset_type="model")
    cancelled = await approvals.cancel_request(TENANT, request.id)
    assert cancelled.status == ApprovalStatus.CANCELLED.value

    with pytest.raises(InvalidTransitionError):
        await approvals.cancel_request(TENANT, request.id)
