"""Prompt Evaluation: automatic (LLM-judge + rule-based), human review,
pairwise comparison, benchmark comparison."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.domain.enums import EvalMetric
from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_evaluation_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_evaluation.evaluation_service import EvaluationService

router = APIRouter(prefix="/prompts/{prompt_id}", tags=["evaluation"])


class RunAutomaticRequest(BaseModel):
    version_id: str
    test_inputs: list[dict]
    metrics: list[EvalMetric]
    reference_outputs: list[str | None] | None = None
    persist_eval_score: bool = False


class RunHumanReviewRequest(BaseModel):
    version_id: str
    score: float
    rationale: str | None = None


class RunPairwiseRequest(BaseModel):
    version_id_a: str
    version_id_b: str
    variables: dict
    metric: EvalMetric = EvalMetric.ACCURACY


class RunBenchmarkRequest(BaseModel):
    version_ids: list[str]
    test_inputs: list[dict]
    metrics: list[EvalMetric]


@router.post("/evaluations/automatic", status_code=201)
async def run_automatic(prompt_id: str, body: RunAutomaticRequest, actor_id: str = Depends(get_current_actor_id), svc: EvaluationService = Depends(get_evaluation_service)):
    run = await svc.run_automatic(
        prompt_id, body.version_id, test_inputs=body.test_inputs, metrics=body.metrics, triggered_by=actor_id,
        reference_outputs=body.reference_outputs, persist_eval_score=body.persist_eval_score,
    )
    return to_dict(run)


@router.post("/evaluations/human-review", status_code=201)
async def run_human_review(prompt_id: str, body: RunHumanReviewRequest, actor_id: str = Depends(get_current_actor_id), svc: EvaluationService = Depends(get_evaluation_service)):
    run = await svc.run_human_review(prompt_id, body.version_id, reviewer_id=actor_id, score=body.score, rationale=body.rationale)
    return to_dict(run)


@router.post("/evaluations/pairwise", status_code=201)
async def run_pairwise(prompt_id: str, body: RunPairwiseRequest, actor_id: str = Depends(get_current_actor_id), svc: EvaluationService = Depends(get_evaluation_service)):
    run = await svc.run_pairwise(prompt_id, body.version_id_a, body.version_id_b, variables=body.variables, triggered_by=actor_id, metric=body.metric)
    return to_dict(run)


@router.post("/evaluations/benchmark", status_code=201)
async def run_benchmark(prompt_id: str, body: RunBenchmarkRequest, actor_id: str = Depends(get_current_actor_id), svc: EvaluationService = Depends(get_evaluation_service)):
    return await svc.run_benchmark(prompt_id, body.version_ids, test_inputs=body.test_inputs, metrics=body.metrics, triggered_by=actor_id)


@router.get("/evaluations/{evaluation_run_id}/results")
async def get_results(prompt_id: str, evaluation_run_id: str, svc: EvaluationService = Depends(get_evaluation_service)):
    return to_dict_list(await svc.get_results(evaluation_run_id))
