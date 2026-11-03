"""Approval policy resolution, review request/approval chains
(parallel + sequential), rejection, and cancellation tests."""
from __future__ import annotations

import pytest

from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.core.exceptions import PermissionDeniedError, ReviewAlreadyDecidedError
from collaboration_platform.domain.enums import AssetType, ReviewStatus
from collaboration_platform.reviews.policy_service import ApprovalPolicyService
from collaboration_platform.reviews.review_service import ReviewService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def _make_asset(repos, name="Asset"):
    ws = await WorkspaceService(repos).create_workspace(name=f"WS-{name}", owner_id="user-1")
    asset = await CollaborationAssetService(repos).register_asset(
        workspace_id=ws.id, asset_type=AssetType.WORKFLOW, external_ref_id=f"ext-{name}", name=name, owner_id="user-1"
    )
    return ws, asset


@pytest.mark.asyncio
async def test_effective_policy_prefers_specific_over_catchall(repos):
    ws, _ = await _make_asset(repos, "policy")
    policy_svc = ApprovalPolicyService(repos)
    await policy_svc.create_policy(ws.id, asset_type=None, required_approvals=1, created_by="user-1")
    await policy_svc.create_policy(ws.id, asset_type="workflow", required_approvals=2, sequential=True, created_by="user-1")

    effective = await policy_svc.get_effective_policy(ws.id, "workflow")
    assert effective.required_approvals == 2
    assert effective.sequential is True

    fallback = await policy_svc.get_effective_policy(ws.id, "document")
    assert fallback.required_approvals == 1


@pytest.mark.asyncio
async def test_parallel_review_requires_threshold_not_unanimity(repos):
    ws, asset = await _make_asset(repos, "parallel")
    svc = ReviewService(repos)
    review = await svc.request_review(
        asset.id, "user-1", reviewer_ids=["rev-a", "rev-b", "rev-c"], required_approvals=2, sequential=False,
    )
    assert review.status == ReviewStatus.PENDING.value

    updated = await svc.approve(review.id, "rev-a")
    assert updated.status == ReviewStatus.IN_REVIEW.value  # 1/2, not yet crossed

    updated = await svc.approve(review.id, "rev-b")
    assert updated.status == ReviewStatus.APPROVED.value  # crossed threshold
    assert updated.decided_at is not None

    # rev-c never had to act; trying to approve now should fail cleanly (already decided)
    with pytest.raises(ReviewAlreadyDecidedError):
        # rev-a already decided
        await svc.approve(review.id, "rev-a")


@pytest.mark.asyncio
async def test_sequential_review_enforces_order(repos):
    ws, asset = await _make_asset(repos, "sequential")
    svc = ReviewService(repos)
    review = await svc.request_review(
        asset.id, "user-1", reviewer_ids=["rev-a", "rev-b"], required_approvals=2, sequential=True,
    )

    with pytest.raises(PermissionDeniedError):
        await svc.approve(review.id, "rev-b")  # rev-a (sequence 0) hasn't gone yet

    await svc.approve(review.id, "rev-a")
    final = await svc.approve(review.id, "rev-b")
    assert final.status == ReviewStatus.APPROVED.value


@pytest.mark.asyncio
async def test_rejection_is_terminal(repos):
    ws, asset = await _make_asset(repos, "reject")
    svc = ReviewService(repos)
    review = await svc.request_review(asset.id, "user-1", reviewer_ids=["rev-a", "rev-b"], required_approvals=2)
    rejected = await svc.reject(review.id, "rev-a", comment="not ready")
    assert rejected.status == ReviewStatus.REJECTED.value

    with pytest.raises(ReviewAlreadyDecidedError):
        await svc.approve(review.id, "rev-b")


@pytest.mark.asyncio
async def test_cancel_review(repos):
    ws, asset = await _make_asset(repos, "cancel")
    svc = ReviewService(repos)
    review = await svc.request_review(asset.id, "user-1", reviewer_ids=["rev-a"])
    cancelled = await svc.cancel(review.id)
    assert cancelled.status == ReviewStatus.CANCELLED.value
