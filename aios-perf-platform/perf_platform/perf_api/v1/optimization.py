"""Auto-Optimization Recommendation Engine: signal-driven generation
plus the guarded proposed -> accepted/rejected -> applied/expired
lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from perf_platform.dependencies.dependencies import get_current_tenant_id, get_recommendation_service
from perf_platform.optimization.optimization_service import RecommendationService
from perf_platform.perf_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/recommendations", tags=["optimization"])


@router.post("/generate/cache")
async def generate_from_cache(tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict_list(await service.generate_from_cache_stats(tenant_id))


class GenerateFromLatencyRequest(BaseModel):
    operation: str


@router.post("/generate/latency")
async def generate_from_latency(
    body: GenerateFromLatencyRequest, tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.generate_from_latency(tenant_id, body.operation))


@router.post("/generate/routing")
async def generate_from_routing(tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict_list(await service.generate_from_routing_decisions(tenant_id))


class GenerateFromBudgetRequest(BaseModel):
    entity_type: str
    entity_id: str


@router.post("/generate/budget")
async def generate_from_budget(
    body: GenerateFromBudgetRequest, tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.generate_from_budget(tenant_id, entity_type=body.entity_type, entity_id=body.entity_id))


@router.get("")
async def list_recommendations(
    status: str | None = None, category: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id, status=status, category=category))


@router.get("/{recommendation_id}")
async def get_recommendation(
    recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service),
):
    return to_dict(await service.get_or_404(tenant_id, recommendation_id))


@router.post("/{recommendation_id}/accept")
async def accept(recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict(await service.accept(tenant_id, recommendation_id))


@router.post("/{recommendation_id}/reject")
async def reject(recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict(await service.reject(tenant_id, recommendation_id))


@router.post("/{recommendation_id}/apply")
async def apply(recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict(await service.apply(tenant_id, recommendation_id))


@router.post("/{recommendation_id}/expire")
async def expire(recommendation_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict(await service.expire(tenant_id, recommendation_id))
