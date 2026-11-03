"""Prompt Optimization: rule-based suggestions, LLM-backed auto-optimize,
few-shot example selection, applying a suggestion as a new draft
version."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.domain.enums import OptimizationObjective
from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_optimization_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_optimization.optimization_service import OptimizationService

router = APIRouter(prefix="/prompts/{prompt_id}/versions/{version_id}/optimization", tags=["optimization"])


class ObjectiveRequest(BaseModel):
    objective: OptimizationObjective = OptimizationObjective.QUALITY


class AutoOptimizeRequest(ObjectiveRequest):
    apply: bool = False


class FewShotRequest(BaseModel):
    max_examples: int = 3
    apply: bool = False


@router.post("/suggest", status_code=201)
async def suggest(prompt_id: str, version_id: str, body: ObjectiveRequest, actor_id: str = Depends(get_current_actor_id), svc: OptimizationService = Depends(get_optimization_service)):
    run = await svc.suggest(prompt_id, version_id, objective=body.objective, triggered_by=actor_id)
    return to_dict(run)


@router.post("/auto-optimize", status_code=201)
async def auto_optimize(prompt_id: str, version_id: str, body: AutoOptimizeRequest, actor_id: str = Depends(get_current_actor_id), svc: OptimizationService = Depends(get_optimization_service)):
    run = await svc.auto_optimize(prompt_id, version_id, objective=body.objective, actor_id=actor_id, apply=body.apply)
    return to_dict(run)


@router.post("/few-shot", status_code=201)
async def optimize_few_shot(prompt_id: str, version_id: str, body: FewShotRequest, actor_id: str = Depends(get_current_actor_id), svc: OptimizationService = Depends(get_optimization_service)):
    run = await svc.optimize_few_shot(prompt_id, version_id, actor_id=actor_id, max_examples=body.max_examples, apply=body.apply)
    return to_dict(run)


@router.post("/suggestions/{suggestion_id}/apply")
async def apply_suggestion(prompt_id: str, version_id: str, suggestion_id: str, actor_id: str = Depends(get_current_actor_id), svc: OptimizationService = Depends(get_optimization_service)):
    return to_dict(await svc.apply_suggestion(suggestion_id, actor_id))


@router.get("/runs/{run_id}/suggestions")
async def get_suggestions(prompt_id: str, version_id: str, run_id: str, svc: OptimizationService = Depends(get_optimization_service)):
    return to_dict_list(await svc.get_suggestions(run_id))


@router.get("/runs")
async def list_runs(prompt_id: str, version_id: str, svc: OptimizationService = Depends(get_optimization_service)):
    return to_dict_list(await svc.list_runs(prompt_id))
