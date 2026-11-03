"""Analytics snapshots (quality/reliability/cost/usage/regression/trend
rollups a dashboard reads instead of recomputing) and the AI
Improvement Loop (failure clustering, regression detection, evidenced
recommendations)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.analytics.improvement_loop import ImprovementLoopService
from eval_platform.analytics.recommendation_service import RecommendationService
from eval_platform.analytics.snapshot_service import AnalyticsSnapshotService
from eval_platform.dependencies.dependencies import (
    get_analytics_snapshot_service,
    get_improvement_loop_service,
    get_recommendation_service,
)
from eval_platform.eval_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/analytics", tags=["analytics"])


class CreateRecommendationRequest(BaseModel):
    workspace_id: str
    category: str
    target_type: str
    title: str
    description: str
    target_id: str | None = None
    evidence: dict


@router.post("/snapshots/quality")
async def build_quality_snapshot(workspace_id: str, period_start: datetime, period_end: datetime, service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service)):
    return to_dict(await service.build_quality_snapshot(workspace_id, period_start=period_start, period_end=period_end))


@router.post("/snapshots/reliability")
async def build_reliability_snapshot(workspace_id: str, period_start: datetime, period_end: datetime, service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service)):
    return to_dict(await service.build_reliability_snapshot(workspace_id, period_start=period_start, period_end=period_end))


@router.post("/snapshots/cost")
async def build_cost_snapshot(workspace_id: str, period_start: datetime, period_end: datetime, service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service)):
    return to_dict(await service.build_cost_snapshot(workspace_id, period_start=period_start, period_end=period_end))


@router.post("/snapshots/usage")
async def build_usage_snapshot(workspace_id: str, period_start: datetime, period_end: datetime, service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service)):
    return to_dict(await service.build_usage_snapshot(workspace_id, period_start=period_start, period_end=period_end))


@router.post("/snapshots/regression")
async def build_regression_snapshot(
    workspace_id: str, evaluation_id: str, period_start: datetime, period_end: datetime, previous_period_start: datetime,
    service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service),
):
    return to_dict(await service.build_regression_snapshot(
        workspace_id, evaluation_id, period_start=period_start, period_end=period_end, previous_period_start=previous_period_start,
    ))


@router.post("/snapshots/trend")
async def build_trend_snapshot(
    workspace_id: str, evaluation_id: str, period_start: datetime, period_end: datetime,
    service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service),
):
    return to_dict(await service.build_trend_snapshot(workspace_id, evaluation_id, period_start=period_start, period_end=period_end))


@router.get("/snapshots")
async def list_snapshots(workspace_id: str, snapshot_type: str | None = None, service: AnalyticsSnapshotService = Depends(get_analytics_snapshot_service)):
    return to_dict_list(await service.list_snapshots(workspace_id, snapshot_type=snapshot_type))


# -- recommendations -----------------------------------------------------------------

@router.post("/recommendations", status_code=201)
async def create_recommendation(body: CreateRecommendationRequest, service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict(await service.create_recommendation(
        body.workspace_id, category=body.category, target_type=body.target_type, title=body.title,
        description=body.description, target_id=body.target_id, evidence=body.evidence,
    ))


@router.get("/recommendations")
async def list_recommendations(workspace_id: str, status: str | None = None, category: str | None = None, service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict_list(await service.list_recommendations(workspace_id, status=status, category=category))


@router.post("/recommendations/{recommendation_id}/accept")
async def accept_recommendation(recommendation_id: str, service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict(await service.accept(recommendation_id))


@router.post("/recommendations/{recommendation_id}/dismiss")
async def dismiss_recommendation(recommendation_id: str, service: RecommendationService = Depends(get_recommendation_service)):
    return to_dict(await service.dismiss(recommendation_id))


# -- improvement loop -----------------------------------------------------------------

@router.post("/improvement-loop/generate")
async def generate_recommendations(
    workspace_id: str, evaluation_id: str, latest_run_id: str | None = None, regression_window: int = 5,
    service: ImprovementLoopService = Depends(get_improvement_loop_service),
):
    return to_dict_list(await service.generate_recommendations(
        workspace_id, evaluation_id, latest_run_id=latest_run_id, regression_window=regression_window,
    ))


@router.get("/improvement-loop/failure-clusters/{run_id}")
async def cluster_run_failures(run_id: str, service: ImprovementLoopService = Depends(get_improvement_loop_service)):
    return await service.cluster_run_failures(run_id)


@router.get("/improvement-loop/regression/{evaluation_id}")
async def detect_score_regression(evaluation_id: str, window: int = 5, service: ImprovementLoopService = Depends(get_improvement_loop_service)):
    return await service.detect_score_regression(evaluation_id, window=window)
