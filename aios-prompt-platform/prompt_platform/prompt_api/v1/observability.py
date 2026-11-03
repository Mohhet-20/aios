"""Prompt Observability: execution history, success rate, analytics
rollups (latency percentiles, cost, model/source breakdown), user
feedback capture."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.prompt_api.dependencies import get_observability_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_observability.observability_service import ObservabilityService

router = APIRouter(prefix="/prompts/{prompt_id}/observability", tags=["observability"])


class FeedbackRequest(BaseModel):
    score: float


@router.get("/executions")
async def execution_history(prompt_id: str, limit: int = 100, svc: ObservabilityService = Depends(get_observability_service)):
    return to_dict_list(await svc.execution_history(prompt_id, limit=limit))


@router.get("/success-rate")
async def success_rate(prompt_id: str, svc: ObservabilityService = Depends(get_observability_service)):
    return {"success_rate": await svc.success_rate(prompt_id)}


@router.get("/analytics")
async def analytics_summary(prompt_id: str, limit: int = 5000, svc: ObservabilityService = Depends(get_observability_service)):
    return await svc.analytics_summary(prompt_id, limit=limit)


@router.post("/executions/{execution_log_id}/feedback")
async def record_feedback(prompt_id: str, execution_log_id: str, body: FeedbackRequest, svc: ObservabilityService = Depends(get_observability_service)):
    return to_dict(await svc.record_user_feedback(execution_log_id, body.score))
