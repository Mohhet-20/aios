"""Quality metric registry (the 20 built-in metrics) plus ad-hoc scoring
and standalone `MetricResultModel` recording — useful for scoring a
single actual/expected pair without a full evaluation run."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.dependencies.dependencies import get_metric_scorer
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.metrics.inputs import MetricInput
from eval_platform.metrics.registry import METRIC_SPECS
from eval_platform.metrics.scorer import MetricScorer

router = APIRouter(prefix="/metrics", tags=["metrics"])


class ComputeMetricsRequest(BaseModel):
    metric_keys: list[str]
    actual_output: Any = None
    expected_output: Any = None
    context_documents: list[str] | None = None
    instructions: list[str] | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None
    success: bool | None = None
    skip_errors: bool = True


class RecordResultRequest(ComputeMetricsRequest):
    workspace_id: str
    subject_type: str
    subject_id: str | None = None


@router.get("/registry")
async def list_metric_specs():
    return [
        {"key": s.key, "name": s.name, "category": s.category, "description": s.description,
         "value_type": s.value_type.value, "higher_is_better": s.higher_is_better}
        for s in METRIC_SPECS
    ]


@router.post("/sync-definitions")
async def sync_definitions(scorer: MetricScorer = Depends(get_metric_scorer)):
    return to_dict_list(await scorer.sync_definitions())


def _build_input(body: ComputeMetricsRequest) -> MetricInput:
    return MetricInput(
        actual_output=body.actual_output, expected_output=body.expected_output, context_documents=body.context_documents,
        instructions=body.instructions, latency_ms=body.latency_ms, prompt_tokens=body.prompt_tokens,
        completion_tokens=body.completion_tokens, cost=body.cost, success=body.success,
    )


@router.post("/compute")
async def compute_metrics(body: ComputeMetricsRequest, scorer: MetricScorer = Depends(get_metric_scorer)):
    return scorer.compute_many(body.metric_keys, _build_input(body), skip_errors=body.skip_errors)


@router.post("/results", status_code=201)
async def record_result(body: RecordResultRequest, scorer: MetricScorer = Depends(get_metric_scorer)):
    metric_input = _build_input(body)
    results = []
    for key in body.metric_keys:
        results.append(to_dict(await scorer.record_result(
            body.workspace_id, key, subject_type=body.subject_type, subject_id=body.subject_id, metric_input=metric_input,
        )))
    return results
