"""Observability & Evaluation: execution timelines, delegation chains,
agent health, cost/latency rollups, and the evaluation-lite metrics —
the Performance / Health Dashboard frontend surfaces."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from agent_platform.agent_api.dependencies import get_analytics_service, get_evaluation_service, get_observability_service
from agent_platform.analytics.analytics_service import AnalyticsService
from agent_platform.evaluation.evaluation_service import EvaluationService
from agent_platform.monitoring.observability_service import ObservabilityService

router = APIRouter(tags=["observability"])


@router.get("/tasks/{task_id}/execution-timeline")
async def execution_timeline(task_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.execution_timeline(task_id)


@router.get("/tasks/{task_id}/delegation-chain")
async def delegation_chain(task_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.delegation_chain(task_id)


@router.get("/agents/{agent_id}/health-summary")
async def agent_health_summary(agent_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.agent_health_summary(agent_id)


@router.get("/analytics/cost-rollup")
async def cost_rollup(agent_id: str | None = None, task_id: str | None = None, svc: AnalyticsService = Depends(get_analytics_service)):
    return await svc.cost_rollup(agent_id=agent_id, task_id=task_id)


@router.get("/tasks/{root_task_id}/evaluation/task-success-rate")
async def task_success_rate(root_task_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.task_success_rate(root_task_id)


@router.get("/tasks/{root_task_id}/evaluation/planning-quality")
async def planning_quality(root_task_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.planning_quality(root_task_id)


@router.get("/tasks/{task_id}/evaluation/reasoning-quality")
async def reasoning_quality_proxy(task_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.reasoning_quality_proxy(task_id)


@router.get("/agents/{agent_id}/evaluation/tool-effectiveness")
async def tool_effectiveness(agent_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.tool_effectiveness(agent_id)


@router.get("/agents/{agent_id}/evaluation/reliability")
async def reliability(agent_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.reliability(agent_id)


@router.get("/tasks/{task_id}/evaluation/collaboration-quality")
async def collaboration_quality(task_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.collaboration_quality(task_id)


@router.get("/agents/{agent_id}/evaluation/failure-recovery-rate")
async def failure_recovery_rate(agent_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.failure_recovery_rate(agent_id)
