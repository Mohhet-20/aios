"""Prompt Testing: single/batch/regression runs, golden test cases,
results."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_testing_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_testing.test_service import PromptTestCase, PromptTestingService

router = APIRouter(prefix="/prompts/{prompt_id}/versions/{version_id}/tests", tags=["testing"])


class TestCaseIn(BaseModel):
    variables: dict = {}
    expected_output: str | None = None
    assertions: list[dict] = []
    max_latency_ms: float | None = None
    max_cost_usd: float | None = None


class RunSingleRequest(BaseModel):
    variables: dict
    expected_output: str | None = None
    assertions: list[dict] = []


class RunBatchRequest(BaseModel):
    cases: list[TestCaseIn]


class GoldenTestCaseRequest(BaseModel):
    name: str
    input_variables: dict
    expected_output: str | None = None
    assertions: list[dict] = []
    max_latency_ms: float | None = None
    max_cost_usd: float | None = None


@router.post("/run-single", status_code=201)
async def run_single(prompt_id: str, version_id: str, body: RunSingleRequest, actor_id: str = Depends(get_current_actor_id), svc: PromptTestingService = Depends(get_testing_service)):
    run = await svc.run_single(prompt_id, version_id, variables=body.variables, expected_output=body.expected_output, assertions=body.assertions, triggered_by=actor_id)
    return to_dict(run)


@router.post("/run-batch", status_code=201)
async def run_batch(prompt_id: str, version_id: str, body: RunBatchRequest, actor_id: str = Depends(get_current_actor_id), svc: PromptTestingService = Depends(get_testing_service)):
    cases = [PromptTestCase(**c.model_dump()) for c in body.cases]
    run = await svc.run_batch(prompt_id, version_id, cases, actor_id)
    return to_dict(run)


@router.post("/run-regression", status_code=201)
async def run_regression(prompt_id: str, version_id: str, actor_id: str = Depends(get_current_actor_id), svc: PromptTestingService = Depends(get_testing_service)):
    run = await svc.run_regression(prompt_id, version_id, actor_id)
    return to_dict(run)


@router.get("/runs/{test_run_id}/results")
async def get_results(prompt_id: str, version_id: str, test_run_id: str, svc: PromptTestingService = Depends(get_testing_service)):
    return to_dict_list(await svc.get_results(test_run_id))


@router.post("/golden-cases", status_code=201)
async def create_golden_case(prompt_id: str, version_id: str, body: GoldenTestCaseRequest, svc: PromptTestingService = Depends(get_testing_service)):
    case = await svc.create_golden_test_case(
        prompt_id, name=body.name, input_variables=body.input_variables, expected_output=body.expected_output,
        assertions=body.assertions, max_latency_ms=body.max_latency_ms, max_cost_usd=body.max_cost_usd,
    )
    return to_dict(case)
