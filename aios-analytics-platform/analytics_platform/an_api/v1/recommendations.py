"""Recommendation Engine: create/list recommendations and drive their
open -> accepted/dismissed -> implemented lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dependencies.dependencies import get_current_tenant_id, get_recommendation_service
from analytics_platform.recommendations.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class CreateRecommendationRequest(BaseModel):
    category: str
    title: str
    description: str = ""
    impact: str = "medium"
    evidence: dict | None = None


@router.post("", status_code=201)
async def create_recommendation(
    body: CreateRecommendationRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.create_recommendation(tenant_id, **body.model_dump()))


@router.get("")
async def list_recommendations(
    category: str | None = None, status: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, category=category, status=status))


@router.get("/{recommendation_id}")
async def get_recommendation(
    recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.get_or_404(tenant_id, recommendation_id))


@router.post("/{recommendation_id}/accept")
async def accept_recommendation(
    recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.accept(tenant_id, recommendation_id))


@router.post("/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.dismiss(tenant_id, recommendation_id))


@router.post("/{recommendation_id}/implement")
async def implement_recommendation(
    recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.implement(tenant_id, recommendation_id))
