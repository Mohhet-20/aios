"""Approval workflows: review requests, approve/reject/cancel, and
policies."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import get_policy_service, get_review_service
from collaboration_platform.reviews.policy_service import ApprovalPolicyService
from collaboration_platform.reviews.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


class RequestReviewRequest(BaseModel):
    asset_id: str
    requested_by: str
    reviewer_ids: list[str]
    version_id: str | None = None
    title: str | None = None
    description: str | None = None
    sequential: bool | None = None
    required_approvals: int | None = None


@router.post("", status_code=201)
async def request_review(body: RequestReviewRequest, service: ReviewService = Depends(get_review_service)):
    return to_dict(await service.request_review(
        body.asset_id, body.requested_by, body.reviewer_ids, version_id=body.version_id, title=body.title,
        description=body.description, sequential=body.sequential, required_approvals=body.required_approvals,
    ))


@router.get("/asset/{asset_id}")
async def list_reviews_for_asset(asset_id: str, service: ReviewService = Depends(get_review_service)):
    return to_dict_list(await service.list_for_asset(asset_id))


@router.get("/{review_request_id}/assignments")
async def list_assignments(review_request_id: str, service: ReviewService = Depends(get_review_service)):
    return to_dict_list(await service.list_assignments(review_request_id))


@router.get("/reviewer/{reviewer_id}")
async def list_for_reviewer(reviewer_id: str, pending_only: bool = False, service: ReviewService = Depends(get_review_service)):
    return to_dict_list(await service.list_for_reviewer(reviewer_id, pending_only=pending_only))


class DecisionRequest(BaseModel):
    reviewer_id: str
    comment: str | None = None


@router.post("/{review_request_id}/approve")
async def approve(review_request_id: str, body: DecisionRequest, service: ReviewService = Depends(get_review_service)):
    return to_dict(await service.approve(review_request_id, body.reviewer_id, comment=body.comment))


@router.post("/{review_request_id}/reject")
async def reject(review_request_id: str, body: DecisionRequest, service: ReviewService = Depends(get_review_service)):
    return to_dict(await service.reject(review_request_id, body.reviewer_id, comment=body.comment))


@router.post("/{review_request_id}/cancel")
async def cancel(review_request_id: str, service: ReviewService = Depends(get_review_service)):
    return to_dict(await service.cancel(review_request_id))


policies_router = APIRouter(prefix="/approval-policies", tags=["reviews"])


class CreatePolicyRequest(BaseModel):
    workspace_id: str
    created_by: str
    asset_type: str | None = None
    required_approvals: int | None = None
    sequential: bool = False
    auto_approve_rules: dict | None = None


@policies_router.post("", status_code=201)
async def create_policy(body: CreatePolicyRequest, service: ApprovalPolicyService = Depends(get_policy_service)):
    return to_dict(await service.create_policy(
        body.workspace_id, asset_type=body.asset_type, required_approvals=body.required_approvals,
        sequential=body.sequential, auto_approve_rules=body.auto_approve_rules, created_by=body.created_by,
    ))


@policies_router.get("/workspace/{workspace_id}")
async def list_policies(workspace_id: str, service: ApprovalPolicyService = Depends(get_policy_service)):
    return to_dict_list(await service.list_for_workspace(workspace_id))
