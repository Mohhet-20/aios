"""Documentation Analytics: raw event recording, most-viewed/failed-
search/tutorial-completion aggregations, feedback scores, broken-link
tracking, and content freshness scoring."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.analytics.analytics_service import (
    AnalyticsEventService,
    BrokenLinkService,
    ContentFreshnessService,
    FeedbackService,
)
from docs_platform.dependencies.dependencies import (
    get_analytics_event_service,
    get_broken_link_service,
    get_content_freshness_service,
    get_current_tenant_id,
    get_feedback_service,
)
from docs_platform.doc_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/analytics", tags=["analytics"])
feedback_router = APIRouter(prefix="/feedback", tags=["analytics"])
broken_links_router = APIRouter(prefix="/broken-links", tags=["analytics"])


class RecordEventRequest(BaseModel):
    event_type: str
    subject_ref: str | None = None
    metadata: dict | None = None


@router.post("/events", status_code=201)
async def record_event(
    body: RecordEventRequest, tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsEventService = Depends(get_analytics_event_service),
):
    return to_dict(await service.record_event(tenant_id, **body.model_dump()))


@router.get("/most-viewed")
async def most_viewed_pages(
    limit: int = 10, tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsEventService = Depends(get_analytics_event_service),
):
    results = await service.most_viewed_pages(tenant_id, limit=limit)
    return [{"subject_ref": ref, "views": count} for ref, count in results]


@router.get("/failed-search-rate")
async def failed_search_rate(
    tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsEventService = Depends(get_analytics_event_service),
):
    return {"rate": await service.failed_search_rate(tenant_id)}


@router.get("/tutorial-completion-rate")
async def tutorial_completion_rate(
    tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsEventService = Depends(get_analytics_event_service),
):
    return {"rate": await service.tutorial_completion_rate(tenant_id)}


@router.get("/content-freshness")
async def content_freshness(
    tenant_id: str = Depends(get_current_tenant_id), service: ContentFreshnessService = Depends(get_content_freshness_service),
):
    results = await service.score_tenant_pages(tenant_id)
    return [{"page_id": page_id, "freshness_score": score} for page_id, score in results]


class SubmitFeedbackRequest(BaseModel):
    subject_ref: str
    score: int
    comment: str | None = None


@feedback_router.post("", status_code=201)
async def submit_feedback(
    body: SubmitFeedbackRequest, tenant_id: str = Depends(get_current_tenant_id), service: FeedbackService = Depends(get_feedback_service),
):
    return to_dict(await service.submit_feedback(tenant_id, **body.model_dump()))


@feedback_router.get("/by-subject/{subject_ref:path}/average")
async def average_feedback_score(
    subject_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: FeedbackService = Depends(get_feedback_service),
):
    return {"average_score": await service.average_score(tenant_id, subject_ref)}


@feedback_router.get("/by-subject/{subject_ref:path}")
async def list_feedback_for_subject(
    subject_ref: str, tenant_id: str = Depends(get_current_tenant_id), service: FeedbackService = Depends(get_feedback_service),
):
    return to_dict_list(await service.list_for_subject(tenant_id, subject_ref))


class ReportBrokenLinkRequest(BaseModel):
    source_ref: str
    url: str


@broken_links_router.post("", status_code=201)
async def report_broken_link(
    body: ReportBrokenLinkRequest, tenant_id: str = Depends(get_current_tenant_id), service: BrokenLinkService = Depends(get_broken_link_service),
):
    return to_dict(await service.report(tenant_id, **body.model_dump()))


@broken_links_router.post("/{link_id}/resolve")
async def resolve_broken_link(
    link_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BrokenLinkService = Depends(get_broken_link_service),
):
    return to_dict(await service.resolve(tenant_id, link_id))


@broken_links_router.get("/unresolved")
async def list_unresolved_broken_links(
    tenant_id: str = Depends(get_current_tenant_id), service: BrokenLinkService = Depends(get_broken_link_service),
):
    return to_dict_list(await service.list_unresolved(tenant_id))
