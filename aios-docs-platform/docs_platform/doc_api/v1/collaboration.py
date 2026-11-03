"""Collaboration: page comments, review requests/decisions, and the
append-only audit trail."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.collaboration.audit_service import AuditLogService
from docs_platform.collaboration.comment_service import CommentService
from docs_platform.collaboration.review_service import ReviewService
from docs_platform.dependencies.dependencies import (
    get_audit_log_service,
    get_comment_service,
    get_current_tenant_id,
    get_review_service,
)
from docs_platform.doc_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/comments", tags=["collaboration"])
reviews_router = APIRouter(prefix="/reviews", tags=["collaboration"])
audit_router = APIRouter(prefix="/audit-log", tags=["collaboration"])


class AddCommentRequest(BaseModel):
    target_ref: str
    author_id: str
    body: str


@router.post("", status_code=201)
async def add_comment(
    body: AddCommentRequest, tenant_id: str = Depends(get_current_tenant_id), service: CommentService = Depends(get_comment_service),
):
    return to_dict(await service.add_comment(tenant_id, **body.model_dump()))


@router.post("/{comment_id}/resolve")
async def resolve_comment(
    comment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CommentService = Depends(get_comment_service),
):
    return to_dict(await service.resolve_comment(tenant_id, comment_id))


@router.get("/by-target/{target_ref:path}")
async def list_comments_for_target(
    target_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: CommentService = Depends(get_comment_service),
):
    return to_dict_list(await service.list_for_target(tenant_id, target_ref))


class RequestReviewRequest(BaseModel):
    page_id: str
    requested_by: str
    reviewer_id: str | None = None


@reviews_router.post("", status_code=201)
async def request_review(
    body: RequestReviewRequest, tenant_id: str = Depends(get_current_tenant_id), service: ReviewService = Depends(get_review_service),
):
    payload = body.model_dump()
    page_id = payload.pop("page_id")
    return to_dict(await service.request_review(tenant_id, page_id, **payload))


class DecideReviewRequest(BaseModel):
    decision: str
    reviewer_id: str
    notes: str = ""


@reviews_router.post("/{review_id}/decide")
async def decide_review(
    review_id: str, body: DecideReviewRequest, tenant_id: str = Depends(get_current_tenant_id), service: ReviewService = Depends(get_review_service),
):
    return to_dict(await service.decide(tenant_id, review_id, **body.model_dump()))


@reviews_router.get("/by-page/{page_id}")
async def list_reviews_for_page(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReviewService = Depends(get_review_service),
):
    return to_dict_list(await service.list_for_page(tenant_id, page_id))


@audit_router.get("/by-target/{target_ref:path}")
async def list_audit_for_target(
    target_ref: str, limit: int = 100, tenant_id: str = Depends(get_current_tenant_id), service: AuditLogService = Depends(get_audit_log_service),
):
    return to_dict_list(await service.list_for_target(tenant_id, target_ref, limit=limit))


@audit_router.get("/recent")
async def list_recent_audit(
    limit: int = 100, tenant_id: str = Depends(get_current_tenant_id), service: AuditLogService = Depends(get_audit_log_service),
):
    return to_dict_list(await service.list_recent(tenant_id, limit=limit))
